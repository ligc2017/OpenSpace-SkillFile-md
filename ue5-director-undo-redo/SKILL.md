---
name: ue5-director-undo-redo
description: UE5 导调系统 Undo/Redo 架构 - Pre/Post State 双状态存储 + 向后 Seek 逆序 Undo 回调
tags: [ue5, unreal-engine, director, undo, redo, playback, state-machine, c++]
---

# UE5 导调系统 Undo/Redo 架构

## 适用场景

- 导调回放系统中，需要支持向后拖动进度条时正确恢复 Actor 状态
- 状态变更不可逆（如 Actor 生成/销毁、动画状态切换），需要保存变更前后的完整状态
- 需要精确控制"撤销到某一时间点"时的执行顺序

## 问题背景

普通回放系统只记录 Actor 的每帧状态快照，向前播放没问题。但**向后 Seek**时：
- 简单地"应用目标时刻的状态"对 Transform 有效（直接设置位置即可）
- 但对"事件型"状态变更（如触发动画、改变材质、生成 Actor）无效——这些操作不能被新状态直接覆盖
- 需要知道"在这之前发生了什么"并逐步撤销

## 核心数据结构

```cpp
// 单次导调操作的记录
struct FDirectorOperation
{
    int64  TimestampMs;      // 操作发生时间
    FString ActorUID;        // 目标 Actor

    // 双状态存储
    TArray<uint8> PreState;  // 操作前状态（用于 Undo）
    TArray<uint8> PostState; // 操作后状态（用于 Redo/正向应用）

    // 操作类型（决定 OnUndo/OnRedo 的行为）
    EDirectorOpType OpType;
};

enum class EDirectorOpType : uint8
{
    Transform      = 0,  // Actor Transform 变更
    AnimTrigger    = 1,  // 动画触发
    Visibility     = 2,  // 显示/隐藏切换
    Spawn          = 3,  // Actor 生成（Undo = 销毁）
    Destroy        = 4,  // Actor 销毁（Undo = 重新生成）
    MaterialSwitch = 5,  // 材质切换
};
```

## 录制时双状态捕获

```cpp
// DirectorRecorderComponent.cpp

void UDirectorRecorderComponent::RecordOperation(
    AActor* TargetActor,
    EDirectorOpType OpType,
    std::function<void()> ExecuteFunc)
{
    FDirectorOperation Op;
    Op.TimestampMs = GetCurrentTimestampMs();
    Op.ActorUID    = GenerateActorUID(TargetActor);
    Op.OpType      = OpType;

    // 捕获操作前状态（PreState）
    Op.PreState = CaptureActorState(TargetActor, OpType);

    // 执行操作
    ExecuteFunc();

    // 捕获操作后状态（PostState）
    Op.PostState = CaptureActorState(TargetActor, OpType);

    // 存入时间线
    RecordedOperations.Add(Op);
}

// 具体调用示例：
void UDirectorRecorderComponent::TriggerAnimation(AActor* Actor, FName AnimName)
{
    RecordOperation(Actor, EDirectorOpType::AnimTrigger, [Actor, AnimName]()
    {
        // 实际触发动画
        if (auto* Mesh = Actor->FindComponentByClass<USkeletalMeshComponent>())
            Mesh->PlayAnimation(LoadAnim(AnimName), false);
    });
}
```

## 回放时正向播放（Redo）

```cpp
// DirectorPlayBackSubsystem.cpp

void UDirectorPlayBackSubsystem::PlayForward(int64 FromMs, int64 ToMs)
{
    // 找出时间范围内的所有操作，按时间正序执行
    TArray<FDirectorOperation*> OpsInRange = GetOperationsInRange(FromMs, ToMs);
    OpsInRange.Sort([](const FDirectorOperation* A, const FDirectorOperation* B)
    {
        return A->TimestampMs < B->TimestampMs;
    });

    for (FDirectorOperation* Op : OpsInRange)
    {
        AActor* Actor = FindActorByUID(Op->ActorUID);
        if (Actor)
            ApplyState(Actor, Op->PostState, Op->OpType); // 应用 PostState
    }
}
```

## 回放时向后 Seek（Undo）

```cpp
void UDirectorPlayBackSubsystem::SeekBackward(int64 FromMs, int64 ToMs)
{
    // 找出需要撤销的操作（时间范围 [ToMs, FromMs]），必须逆序撤销！
    TArray<FDirectorOperation*> OpsToUndo = GetOperationsInRange(ToMs, FromMs);
    
    // 关键：逆序执行 Undo，保证依赖关系正确
    // 例如：Op1 在 T=100 修改了材质，Op2 在 T=200 基于新材质又做了修改
    // 向后 Seek 到 T=50 时，必须先 Undo Op2，再 Undo Op1
    OpsToUndo.Sort([](const FDirectorOperation* A, const FDirectorOperation* B)
    {
        return A->TimestampMs > B->TimestampMs; // 降序排列
    });

    for (FDirectorOperation* Op : OpsToUndo)
    {
        AActor* Actor = FindActorByUID(Op->ActorUID);
        if (Actor)
        {
            OnUndo(Actor, Op);
        }
    }
}

void UDirectorPlayBackSubsystem::OnUndo(AActor* Actor, const FDirectorOperation* Op)
{
    switch (Op->OpType)
    {
    case EDirectorOpType::Transform:
    case EDirectorOpType::AnimTrigger:
    case EDirectorOpType::Visibility:
    case EDirectorOpType::MaterialSwitch:
        // 直接应用 PreState（恢复到操作前的状态）
        ApplyState(Actor, Op->PreState, Op->OpType);
        break;

    case EDirectorOpType::Spawn:
        // Undo "生成" = 销毁该 Actor
        Actor->Destroy();
        break;

    case EDirectorOpType::Destroy:
        // Undo "销毁" = 重新生成，并恢复 PreState（销毁前的状态）
        {
            FActorSpawnParameters Params;
            Params.Name = FName(*Op->ActorUID);
            AActor* RestoredActor = GetWorld()->SpawnActor<AActor>(
                GetActorClassFromPreState(Op->PreState), Params);
            if (RestoredActor)
                ApplyState(RestoredActor, Op->PreState, Op->OpType);
        }
        break;
    }
}
```

## 完整 Seek 流程

```cpp
void UDirectorPlayBackSubsystem::SeekToTime(float TargetTimeSeconds)
{
    int64 TargetMs  = static_cast<int64>(TargetTimeSeconds * 1000.0f);
    int64 CurrentMs = static_cast<int64>(CurrentPlaybackTime * 1000.0f);

    if (TargetMs > CurrentMs)
    {
        // 向前 Seek：正向应用 [CurrentMs, TargetMs] 的所有操作
        PlayForward(CurrentMs, TargetMs);
    }
    else if (TargetMs < CurrentMs)
    {
        // 向后 Seek：逆序 Undo [TargetMs, CurrentMs] 的所有操作
        SeekBackward(CurrentMs, TargetMs);
    }

    CurrentPlaybackTime = TargetTimeSeconds;
}
```

## 状态快照大小优化

```cpp
// 并不是所有类型的 Op 都需要完整的 Actor 状态
// 根据 OpType 只捕获相关的最小状态

TArray<uint8> CaptureActorState(AActor* Actor, EDirectorOpType OpType)
{
    TArray<uint8> State;
    switch (OpType)
    {
    case EDirectorOpType::Transform:
        // 只需要 40 字节的 TransformPOD
        {
            FTransformPOD Pod = ToTransformPOD(Actor->GetActorTransform());
            State.SetNumUninitialized(sizeof(FTransformPOD));
            FMemory::Memcpy(State.GetData(), &Pod, sizeof(FTransformPOD));
        }
        break;

    case EDirectorOpType::Visibility:
        // 只需要 1 字节的可见性标志
        State.Add(Actor->IsHidden() ? 0 : 1);
        break;

    case EDirectorOpType::MaterialSwitch:
        // 需要材质路径字符串
        // 序列化 FString → UTF8 字节
        {
            FString MatPath = GetCurrentMaterialPath(Actor);
            FTCHARToUTF8 UTF8(*MatPath);
            State.Append(reinterpret_cast<const uint8*>(UTF8.Get()), UTF8.Length());
        }
        break;
    }
    return State;
}
```

## 注意事项

1. **逆序 Undo 是必须的** — 如果有 Op 之间存在依赖（后操作依赖前操作的结果），顺序 Undo 会产生错误状态
2. **Spawn/Destroy 的 Undo 代价高** — 销毁/重建 Actor 会触发完整的 BeginPlay/EndPlay 周期，影响性能；考虑用 SetActorHiddenInGame + 对象池代替真正的 Destroy
3. **PreState 存储时机** — 必须在执行操作之前立即捕获，不能在 Tick 结束时批量捕获（可能已经被覆盖）
4. **Actor 指针安全** — 存储 `ActorUID` 而不是 `AActor*`，Undo 时通过 Registry 重新查找；直接存指针在 Undo Spawn/Destroy 后会悬垂
5. **操作幂等性** — `ApplyState` 应设计为幂等的（多次调用同一 State 结果相同），避免重复应用导致状态漂移

## 来源项目

`ScenePlayBack` 插件 (`TestPlayBack` 项目) — `DirectorPlayBackSubsystem.h` + `DirectorRecorderComponent.h`

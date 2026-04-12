---
name: ue5-blueprint-wildcard-customthunk
description: UE5 蓝图 Wildcard USTRUCT 接口 - 用 CustomThunk 实现接受任意结构体的蓝图节点
tags: [ue5, unreal-engine, blueprint, customthunk, wildcard, ustruct, reflection, c++]
---

# UE5 蓝图 Wildcard USTRUCT 接口（CustomThunk）

## 适用场景

- 需要一个蓝图节点能接受"任意 USTRUCT"作为输入（类似 `Print Struct`）
- 录制系统中，`SubmitSnapshot` 节点需要接受任意用户自定义数据结构
- 避免为每种结构体写一个专用蓝图函数

## 核心机制

标准 `UFUNCTION` 不支持泛型参数。`CustomThunk` 允许你手动处理 Blueprint VM 的栈帧，绕过 UE 的类型检查，从而接受 Wildcard（通配符）结构体。

## 头文件声明

```cpp
// ScenePlayBackRecordableComponent.h

UCLASS(ClassGroup=(ScenePlayBack), meta=(BlueprintSpawnableComponent))
class SCENEPLAYBACKCOLLECT_API UScenePlayBackRecordableComponent : public UActorComponent
{
    GENERATED_BODY()

public:
    /**
     * 提交任意 USTRUCT 数据快照
     * CustomThunk 版本 - 接受 Wildcard 结构体
     *
     * @param InStruct  任意 USTRUCT（蓝图中显示为 Wildcard 引脚）
     * @param SchemaId  数据结构类型 ID（与协议定义对应）
     */
    UFUNCTION(BlueprintCallable, CustomThunk,
              meta = (CustomStructureParam = "InStruct",
                      DisplayName = "Submit Snapshot"))
    void SubmitSnapshot(const int32& InStruct, int32 SchemaId);

    // CustomThunk 实际执行函数
    DECLARE_FUNCTION(execSubmitSnapshot);
};
```

**关键 meta 说明：**
- `CustomThunk` — 告诉 UHT 不要自动生成 `exec` 函数，由我们手写
- `CustomStructureParam = "InStruct"` — 将 `InStruct` 参数标记为 Wildcard，蓝图中可连接任意结构体
- 参数类型声明为 `const int32&` 只是占位，实际类型在运行时由 Thunk 解析

## CPP 实现

```cpp
// ScenePlayBackRecordableComponent.cpp

// 使用占位宏声明（防止 UHT 生成默认实现）
void UScenePlayBackRecordableComponent::SubmitSnapshot(const int32& InStruct, int32 SchemaId)
{
    // 这个函数体不会被调用，实际走 execSubmitSnapshot
    checkNoEntry();
}

DEFINE_FUNCTION(UScenePlayBackRecordableComponent::execSubmitSnapshot)
{
    // Step 1: 从 BP 栈中读取 InStruct 参数
    // Stack.StepCompiledIn<FStructProperty> 会解析实际的结构体类型
    Stack.MostRecentPropertyAddress = nullptr;
    Stack.MostRecentProperty = nullptr;
    Stack.StepCompiledIn<FStructProperty>(nullptr);

    // 获取结构体的内存地址和类型信息
    void* StructPtr = Stack.MostRecentPropertyAddress;
    FStructProperty* StructProp = CastField<FStructProperty>(Stack.MostRecentProperty);

    // Step 2: 读取 SchemaId 参数
    P_GET_PROPERTY(FIntProperty, SchemaId);

    // Step 3: 结束参数读取（必须调用）
    P_FINISH;

    // Step 4: 在 Native 代码中安全使用结构体
    P_NATIVE_BEGIN;

    if (StructPtr && StructProp)
    {
        UScriptStruct* StructType = StructProp->Struct;

        // 将结构体序列化为字节数组
        TArray<uint8> Payload;
        Payload.SetNumUninitialized(StructType->GetStructureSize());
        StructType->CopyScriptStruct(Payload.GetData(), StructPtr);

        // 提交到 SessionWriter
        if (UScenePlayBackLocalRecorderSubsystem* Recorder =
            GetWorld()->GetSubsystem<UScenePlayBackLocalRecorderSubsystem>())
        {
            Recorder->SubmitSnapshot(
                GetOwner(),
                static_cast<uint16>(SchemaId),
                Payload
            );
        }
    }
    else
    {
        UE_LOG(LogPlayBack, Warning, TEXT("SubmitSnapshot: Invalid struct input"));
    }

    P_NATIVE_END;
}
```

## 蓝图使用效果

蓝图中调用 `Submit Snapshot` 节点时：
- `In Struct` 引脚显示为灰色 Wildcard 类型
- 连接任意 USTRUCT 变量后，引脚自动变为对应结构体类型
- `Schema Id` 引脚填写协议定义的数字 ID

```
[My Transform Data (FMyTransformStruct)] ─→ [Submit Snapshot] ─→ (exec)
[Schema Id: 1] ──────────────────────────→ [Submit Snapshot]
```

## 自定义结构体示例

```cpp
// 用户定义的数据结构，只需加 USTRUCT 即可在蓝图中使用
USTRUCT(BlueprintType)
struct FMyActorState
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadWrite)
    FVector Location;

    UPROPERTY(BlueprintReadWrite)
    float Health;

    UPROPERTY(BlueprintReadWrite)
    int32 TeamID;
};

// 蓝图中直接传入 FMyActorState 变量到 Submit Snapshot 节点即可
```

## 注意事项

1. **`P_GET_PROPERTY` 参数顺序** — Thunk 中读取参数的顺序必须与 `UFUNCTION` 声明中的参数顺序完全一致，否则栈解析错误会导致崩溃
2. **`P_FINISH` 必须调用** — 即使后续有 `return`，也必须先调用 `P_FINISH`（宏展开包含 `Stack.Code += ...`），否则 BP VM 栈指针偏移错误
3. **`P_NATIVE_BEGIN / P_NATIVE_END`** — 这两个宏包裹实际业务逻辑，提供异常处理边界
4. **Wildcard 引脚颜色** — 未连接时引脚为灰色；一旦连接，UE 会自动推断类型并改变颜色（绿色=结构体）
5. **只读结构体** — Thunk 中拿到的是 `const void*`，修改原始结构体需要去掉 `const`（对应 `UFUNCTION` 参数也去掉 `const`）
6. **打包不稳定** — 如果结构体内有 `FString`/`TArray` 等非 POD 类型，`CopyScriptStruct` 会处理深拷贝；但跨端传输时需要先序列化为纯字节流

## Build.cs 依赖

```csharp
// 使用 StructProperty 和 Blueprint VM 相关功能不需要额外依赖
// 只需确保有：
PublicDependencyModuleNames.AddRange(new string[]
{
    "Core", "CoreUObject", "Engine"
});
```

## 来源项目

`ScenePlayBack` 插件 (`TestPlayBack` 项目) — `ScenePlayBackRecordableComponent.h`

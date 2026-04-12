---
name: ue5-subsystem-layering
description: UE5 WorldSubsystem + GameInstanceSubsystem 分层设计 - 回放/录制系统的生命周期分层最佳实践
tags: [ue5, unreal-engine, subsystem, worldsubsystem, gameinstancesubsystem, architecture, lifecycle, c++]
---

# UE5 WorldSubsystem + GameInstanceSubsystem 分层设计

## 适用场景

- 插件需要同时管理"关卡级"数据和"跨关卡持久"数据
- 回放/录制系统中，注册表（Registry）需要在关卡切换后保留，但控制器应随关卡重置
- 避免使用全局单例（UGameplayStatics 的 GetGameInstance 等），利用 UE 的 Subsystem 依赖注入

## 分层原则

| Subsystem 类型 | 生命周期 | 适合存放 |
|----------------|----------|----------|
| `UWorldSubsystem` | 随 UWorld 创建/销毁（每次关卡切换重新创建） | 回放控制器、当前场景状态、帧缓存 |
| `UGameInstanceSubsystem` | 随 GameInstance 存活（游戏启动到退出，跨关卡持久） | Actor 注册表、配置、连接池、持久 ID 映射 |
| `ULocalPlayerSubsystem` | 随玩家存活（多人游戏每个玩家独立） | UI 状态、输入绑定 |
| `UEngineSubsystem` | 引擎全局单例 | 编辑器工具、全局配置 |

## 架构示例：导调回放系统分层

```
GameInstance 级（跨关卡持久）
└── UDirectorActorRegistry        ← Actor 注册表（ActorUID → Actor Class 映射）

World 级（关卡内有效）
└── UDirectorPlayBackSubsystem    ← 回放控制（播放/暂停/Seek）
    └── 依赖 → UDirectorActorRegistry（通过 GameInstance 获取）
```

## GameInstanceSubsystem：Actor 注册表

```cpp
// DirectorActorRegistry.h

UCLASS()
class SCENEPLAYBACKDIRECTOR_API UDirectorActorRegistry : public UGameInstanceSubsystem
{
    GENERATED_BODY()

public:
    // USubsystem 接口
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual void Deinitialize() override;

    // 注册 Actor（录制时调用）
    void RegisterActor(const FString& ActorUID, AActor* Actor);

    // 查找 Actor（回放时调用）
    AActor* FindActor(const FString& ActorUID) const;

    // 清理已销毁的弱引用（懒清理）
    void CleanupStaleEntries();

private:
    // 弱引用 Map：Actor 销毁后自动失效，不会造成悬垂指针
    mutable TMap<FString, TWeakObjectPtr<AActor>> ActorRegistry;
};
```

```cpp
// DirectorActorRegistry.cpp

void UDirectorActorRegistry::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    UE_LOG(LogDirector, Log, TEXT("DirectorActorRegistry initialized (GameInstance level)"));
}

void UDirectorActorRegistry::RegisterActor(const FString& ActorUID, AActor* Actor)
{
    if (!Actor) return;
    ActorRegistry.Add(ActorUID, TWeakObjectPtr<AActor>(Actor));
}

AActor* UDirectorActorRegistry::FindActor(const FString& ActorUID) const
{
    // 惰性清理：查找时顺带清理失效条目
    if (const TWeakObjectPtr<AActor>* WeakPtr = ActorRegistry.Find(ActorUID))
    {
        if (WeakPtr->IsValid())
            return WeakPtr->Get();
        
        // 弱引用已失效（Actor 被销毁），清理
        ActorRegistry.Remove(ActorUID);
    }
    return nullptr;
}

void UDirectorActorRegistry::CleanupStaleEntries()
{
    TArray<FString> ToRemove;
    for (const auto& Pair : ActorRegistry)
    {
        if (!Pair.Value.IsValid())
            ToRemove.Add(Pair.Key);
    }
    for (const FString& Key : ToRemove)
        ActorRegistry.Remove(Key);
}
```

## WorldSubsystem：回放控制器

```cpp
// DirectorPlayBackSubsystem.h

UCLASS()
class SCENEPLAYBACKDIRECTOR_API UDirectorPlayBackSubsystem : public UWorldSubsystem
{
    GENERATED_BODY()

public:
    // USubsystem 接口
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual void Deinitialize() override;

    // 回放控制
    UFUNCTION(BlueprintCallable)
    void Play();

    UFUNCTION(BlueprintCallable)
    void Pause();

    UFUNCTION(BlueprintCallable)
    void SeekToTime(float TimeSeconds);

private:
    // 从 GameInstance 获取持久 Registry（跨关卡有效）
    UDirectorActorRegistry* GetActorRegistry() const;

    float CurrentPlaybackTime = 0.0f;
    bool  bIsPlaying = false;

    // Seek 防并发
    std::atomic<int32> SeekSerial{ 0 };
};
```

```cpp
// DirectorPlayBackSubsystem.cpp

void UDirectorPlayBackSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    
    // WorldSubsystem 在每次关卡加载时重新初始化
    CurrentPlaybackTime = 0.0f;
    bIsPlaying = false;
    SeekSerial.store(0);
    
    UE_LOG(LogDirector, Log, TEXT("DirectorPlayBackSubsystem initialized for world: %s"),
           *GetWorld()->GetName());
}

UDirectorActorRegistry* UDirectorPlayBackSubsystem::GetActorRegistry() const
{
    // 通过 GameInstance 获取持久 Subsystem
    if (UGameInstance* GI = GetWorld()->GetGameInstance())
        return GI->GetSubsystem<UDirectorActorRegistry>();
    return nullptr;
}
```

## 外部使用方式

```cpp
// 蓝图或其他 Actor 中获取 Subsystem

// 获取 World 级 Subsystem（当前关卡）
UDirectorPlayBackSubsystem* PlayBack = GetWorld()->GetSubsystem<UDirectorPlayBackSubsystem>();
if (PlayBack)
    PlayBack->Play();

// 获取 GameInstance 级 Subsystem（跨关卡持久）
UDirectorActorRegistry* Registry = GetGameInstance()->GetSubsystem<UDirectorActorRegistry>();
if (Registry)
    Registry->RegisterActor(MyUID, MyActor);
```

## 关卡切换行为

```
关卡 A 加载：
  → UDirectorActorRegistry::Initialize()   [首次创建，GameInstance 级]
  → UDirectorPlayBackSubsystem::Initialize() [World 级，针对关卡 A]

切换到关卡 B：
  → UDirectorPlayBackSubsystem::Deinitialize() [关卡 A 的回放控制器销毁]
  → 关卡 A 的所有 Actor 销毁
  → UDirectorActorRegistry 继续存活！[GameInstance 级，跨关卡]
    - 关卡 A 的弱引用自动失效（Actor 已销毁）
    - 保留其他持久数据（如配置、会话 ID）
  → UDirectorPlayBackSubsystem::Initialize() [关卡 B 的新回放控制器创建]
```

## 弱引用 Registry 的 GC 安全性

```cpp
// TWeakObjectPtr 在 UE GC 后自动置 null，不会造成悬垂指针
// IsValid() 会同时检查：
// 1. 指针非 null
// 2. 对象未被标记为 PendingKill
// 3. 对象未被 GC 回收

TWeakObjectPtr<AActor> WeakActor = SomeActor;

// GC 运行后...
if (WeakActor.IsValid())
{
    // 安全，Actor 还存活
    WeakActor->DoSomething();
}
else
{
    // Actor 已被 GC 回收或手动 Destroy，弱引用自动失效
}
```

## Build.cs 依赖

```csharp
// WorldSubsystem 和 GameInstanceSubsystem 都在 Engine 模块中，无需额外依赖
PublicDependencyModuleNames.AddRange(new string[]
{
    "Core",
    "CoreUObject",
    "Engine"         // 包含 UWorldSubsystem, UGameInstanceSubsystem
});
```

## 注意事项

1. **不要在 WorldSubsystem 中持有跨关卡数据** — WorldSubsystem 随关卡销毁，存在其中的数据会丢失
2. **不要在 GameInstanceSubsystem 中持有 UWorld\* 指针** — GameInstance 跨关卡，但 UWorld 每次切换都会重建
3. **`mutable` TMap 用于惰性清理** — `FindActor` 是 `const` 方法，但需要修改 Map（清理失效条目），用 `mutable` 解决
4. **Subsystem 依赖顺序** — 如果 WorldSubsystem 需要在 Initialize 时访问 GameInstanceSubsystem，GameInstanceSubsystem 必定已初始化（GameInstance 生命周期更长）
5. **编辑器下的行为** — 在 PIE（Play In Editor）中，每次 Play 都会重建 World 和 WorldSubsystem，但 GameInstanceSubsystem 只在首次 Play 创建（如果 `bUsesSeparateProcess = false`）

## 来源项目

`ScenePlayBack` 插件 (`TestPlayBack` 项目) — `DirectorPlayBackSubsystem.h` + `DirectorActorRegistry.h`

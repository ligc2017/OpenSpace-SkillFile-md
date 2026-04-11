# UE5 ScenePlayBack Actor 轨迹同步

## 描述
UE5 ScenePlayBack 插件中录制/回放 Actor 轨迹同步的完整实现模式。
涵盖专用回放 Actor 设计、快照缓冲管理、Seek 状态修复、时序陷阱等生产级经验。

技术栈：UE5.3/5.4、C++、ScenePlayBack 插件、环形缓冲插值

---

## 1. 架构总览

```
录制端：
  ATrainActor::BeginPlay()
    → DataCollector->CharacterId = TrainActorId   ← 必须在 Super 之前
    → Super::BeginPlay()
      → UTrainDataCollector::BeginPlay()
          → ActorIdOverride = CharacterId
          → SimOrbitCenter = Owner->GetActorLocation()  ← 圆心绑定
  UTrainDataCollector::TickComponent()
    → FillSnapshot(Snap)
    → SubmitSnapshotNative(FTrainSnapshot::StaticStruct(), &Snap)
      → 写入 [FScenePlayBackRecordablePayloadHeader][POD RawMemcpy]

回放端：
  APlayBackController::UpdateActors(AbsTime)
    → GetOrCreateActor(SchemaId, ActorID, DataTypeId=1)
      → spawn ATrainPlayBackActor   ← 专用回放类，非 ATrainActor
    → comp->OnReceiveData(Payload, Timestamp)
      → 解析 Header → 提取 Location/Rotation → AddSnapshot()
    → comp->UpdatePlayback(CurrentAbsTime)
      → 二分查找 + 线性插值 → SetActorLocationAndRotation
```

---

## 2. 问题与解决方案

### 2.1 轨道圆心未绑定（Actor 全叠在原点）

**症状**：15 个 Actor 轨迹全部重叠在世界原点  
**原因**：`SimOrbitCenter` 默认 `FVector::ZeroVector`，未绑定 Actor 放置位置

**修复**：两处都要设置

```cpp
// ATrainActor::BeginPlay() —— Super 之后（World 已初始化）
Super::BeginPlay();
DataCollector->SimOrbitCenter = GetActorLocation();

// UTrainDataCollector::BeginPlay() —— 兜底防御
if (AActor* Owner = GetOwner())
    SimOrbitCenter = Owner->GetActorLocation();
```

---

### 2.2 OnReceiveData 不能调 Super

**症状**：回放 Actor 不动，或位置跳帧  
**原因**：基类 `FPlayBackTransformDecoder` 期望 Payload 从字节 0 起就是 `FVector+FRotator`，无法识别 `RecordablePayloadHeader`，会把 Header 字节误读为坐标

**正确实现**（`UScenePlayBackRecordableComponent::OnReceiveData`）：

```cpp
void UScenePlayBackRecordableComponent::OnReceiveData(const TArray<uint8>& Payload, int64 Timestamp)
{
    // 1. 解析 RecordablePayloadHeader
    // 2. 用反射提取 Location / Rotation 字段
    // 3. AddSnapshot(NewSnap)  ← 写入插值缓冲
    // 不调 Super::OnReceiveData()  ← 关键！
}
```

---

### 2.3 专用回放 Actor：ATrainPlayBackActor

**症状**：回放时 `ATrainActor` 的 `FillSnapshot` 末尾调 `SetActorLocation` 覆盖插值结果  
**根本解决**：新建专用回放类，无采集 Tick

```cpp
// ATrainPlayBackActor 构造函数
ATrainPlayBackActor::ATrainPlayBackActor()
{
    PrimaryActorTick.bCanEverTick = false;  // 无 Tick

    MeshComponent = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("MeshComponent"));
    RootComponent = MeshComponent;

    RecordableComponent = CreateDefaultSubobject<UScenePlayBackRecordableComponent>(TEXT("RecordableComponent"));

    // ★ 必须显式设置，否则 OnReceiveData CRC 校验失败，快照永远不写入
    RecordableComponent->SnapshotType = FTrainSnapshot::StaticStruct();
    RecordableComponent->bAutoApplyTransform = true;
    RecordableComponent->bWriteToLocalRecorder = false;  // 不写录制文件
    RecordableComponent->RecordableDataTypeId = 1;
}
```

**编辑器配置**：`APlayBackController` → Details → `ActorClassMapById[1] = ATrainPlayBackActor`

---

### 2.4 回放场景误 spawn ATrainActor 的防御

**症状**：`DUPLICATE TrainActorId=N` 报错，录制逻辑污染回放数据  
**修复**：`ATrainActor::BeginPlay()` 开头检测 `APlayBackController`：

```cpp
void ATrainActor::BeginPlay()
{
    if (UWorld* W = GetWorld())
    {
        for (TActorIterator<APlayBackController> It(W); It; ++It)
        {
            // 回放场景：关闭采集，仅执行生命周期初始化
            DataCollector->bWriteToLocalRecorder = false;
            DataCollector->SetComponentTickEnabled(false);
            Super::BeginPlay();
            return;
        }
    }
    // 正常录制逻辑...
}
```

---

### 2.5 Seek 后 Actor 静止（最重要）

**症状**：拖进度条 10s→20s，再回到 10s，Actor 静止；直到播放追上 20s 才恢复  
**根本原因**：

```
回放模式 AddSnapshot 第104行：
  if (NewSnap.Timestamp <= SnapAt(SnapshotCount-1).Timestamp) return;

Seek 20s→10s 后：
  缓冲尾部 Timestamp ≈ 20s
  新喂入的 10s 快照全部被丢弃
  UpdatePlayback(10s) → PrevIdx = -1 → Actor 静止
```

**修复**：`APlayBackController::ApplySeekResult()` 中，合并 FrameCache 之前清空所有组件缓冲：

```cpp
void APlayBackController::ApplySeekResult(...)
{
    // ... Serial 校验、Director 通知 ...

    CurrentRelativeTimeMs = NewRelativeTimeMs;
    LastProcessedFrameIndex = 0;
    LastUpdateAbsTime = StartTimestamp;

    // ★ Seek 后必须清空缓冲，否则旧时间戳阻止新快照写入
    for (auto& Pair : ActorComponentCache)
    {
        if (Pair.Value)
            Pair.Value->ResetPlaybackBuffer();
    }

    // 合并预读帧...
    for (auto& Pair : PreloadedFrames)
        FrameCache.Add(Pair.Key, MoveTemp(Pair.Value));

    UpdateActors(TargetAbsTime);
}
```

---

### 2.6 模拟状态机死亡导致"假静止"

**症状**：录制 44~47s 时所有 Actor 停止移动  
**原因**：`SimHealthDecayRate=2/s`，初始血量 60~100，约 30~50s 后进入死亡状态；死亡分支不推进 `SimOrbitAngle`

**调整方案**：

| 方案 | 修改 | 效果 |
|------|------|------|
| 减慢衰减 | `SimHealthDecayRate = 0.5f` | 死亡推迟到 120~200s |
| 关闭死亡 | `SimHealthDecayRate = 0.f` | 永不死亡 |
| 死亡仍移动 | 死亡分支也执行 `SimOrbitAngle += SimOrbitDegreesPerSec * DeltaTime` | 保留死亡逻辑但不静止 |

---

## 3. 关键时序陷阱：ActorIdOverride 赋值顺序

```cpp
// ATrainActor::BeginPlay()
// ★ 必须在 Super::BeginPlay() 之前赋值！
DataCollector->CharacterId = TrainActorId;   // ← 先
DataCollector->TeamId = ...;
Super::BeginPlay();  // ← UTrainDataCollector::BeginPlay() 在此执行
                     //   内部 ActorIdOverride = CharacterId 依赖上面的赋值
```

若在 Super 之后赋值：15 个 Actor 的 `ActorIdOverride` 全为默认值 1，回放只 spawn 1 个 Actor。

---

## 4. RecordablePayloadHeader 格式

```
[FScenePlayBackRecordablePayloadHeader]  ← Magic + Version + StructNameCrc32 + PayloadSize
[StructBytes]                            ← Version=2: RawMemcpy (POD); Version=1: 反射序列化
```

- **Version=2 (RawMemcpy)**：纯 POD 结构体，零 tag 开销，推荐
- **Version=1 (Reflected)**：含 `FString`/`TArray` 等堆字段时的回退路径
- `StructNameCrc32`：`FCrc::StrCrc32(*Struct->GetPathName())`，回放时校验类型一致性

---

## 5. SnapshotType 必须显式设置

- `UTrainDataCollector` 构造中 `SnapshotType = nullptr`（默认值）
- 第一次调 `SubmitSnapshotNative` 时自动设置（录制侧 OK）
- **回放专用 Actor 构造函数必须显式设置**，否则 `OnReceiveData` CRC 校验因 `nullptr` 跳过，快照永远不写入缓冲

---

## 6. Build.cs 依赖（PlayBackIntegrationTest 模块）

```csharp
PrivateDependencyModuleNames.AddRange(new string[]
{
    "ScenePlayBack",           // 类型定义、ScenePlayBackTypes
    "ScenePlayBackCollect",    // UScenePlayBackRecordableComponent
    "ScenePlayBackPlayback",   // UPlayBackComponent、AddSnapshot、UpdatePlayback
    "ScenePlayBackDirector",   // Director 映射
});
```

---

## 7. 涉及文件清单

| 文件 | 改动说明 |
|------|----------|
| `TrainDataCollector.cpp` | BeginPlay 新增 SimOrbitCenter 绑定 |
| `ScenePlayBackRecordableComponent.cpp` | OnReceiveData 重构为 AddSnapshot 路径 |
| `TrainActor.cpp` | BeginPlay 新增回放场景保护（检测 APlayBackController） |
| `TrainPlayBackActor.h/.cpp` | 新建回放专用 Actor |
| `PlayBackController.cpp` | ApplySeekResult 新增 ResetPlaybackBuffer 调用 |

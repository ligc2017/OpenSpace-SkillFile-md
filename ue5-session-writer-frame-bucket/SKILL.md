---
name: ue5-session-writer-frame-bucket
description: UE5 录制系统 SessionWriter 帧桶聚合设计 - 时间帧分桶 + (ActorID,DataType) 融合去重 + 压缩写入
tags: [ue5, unreal-engine, recording, playback, serialization, compression, performance, c++]
---

# UE5 SessionWriter 帧桶聚合设计

## 适用场景

- 多 Actor 实时录制系统，需要将每帧多个 Actor 的数据合并为一个包
- 同一帧内同一 Actor 可能提交多次（如多个组件各自提交 Transform），需要去重保留最新值
- 录制文件需要压缩存储（降低磁盘/网络带宽）

## 核心数据结构

```cpp
// 单个 Actor 单帧的数据快照
struct FActorSnapshot
{
    FString    ActorUID;     // 唯一 ID（由 FNV-1a 生成）
    uint8      DataType;     // 数据类型（0=Transform, 1=AnimPose, ...）
    TArray<uint8> Payload;   // 序列化后的数据字节
};

// 一个时间帧桶：包含该帧所有 Actor 的快照
struct FFrameBucket
{
    int64 TimestampMs;                         // 帧时间戳（毫秒）
    TMap<FString, FActorSnapshot> Snapshots;   // Key = ActorUID+DataType，融合去重用
};

// SessionWriter 内部状态
class FScenePlayBackSessionWriter
{
    TMap<int64, FFrameBucket> FrameBuckets;    // Key = 帧时间戳（对齐到帧间隔）
    int32 FrameIntervalMs = 33;                // 默认 30fps，约 33ms/帧
    // ...
};
```

## 帧桶算法

### Step 1：时间戳对齐到帧桶

```cpp
// 将任意时间戳对齐到帧间隔边界（向下取整）
int64 AlignToFrameBucket(int64 TimestampMs, int32 FrameIntervalMs)
{
    return (TimestampMs / FrameIntervalMs) * FrameIntervalMs;
}

// 示例：帧间隔 33ms
// 时间 105ms → 对齐到 99ms（第 3 帧桶：99~132ms）
// 时间 110ms → 对齐到 99ms（同一帧桶）
// 时间 133ms → 对齐到 132ms（第 4 帧桶）
```

### Step 2：按 (ActorUID, DataType) 融合去重

```cpp
void FScenePlayBackSessionWriter::SubmitSnapshot(
    int64 TimestampMs,
    const FString& ActorUID,
    uint8 DataType,
    const TArray<uint8>& Payload)
{
    // 对齐到帧桶
    int64 BucketKey = AlignToFrameBucket(TimestampMs, FrameIntervalMs);
    
    // 获取或创建帧桶
    FFrameBucket& Bucket = FrameBuckets.FindOrAdd(BucketKey);
    Bucket.TimestampMs = BucketKey;
    
    // 融合键 = ActorUID + DataType（字符串拼接，简单高效）
    FString MergeKey = ActorUID + FString::Printf(TEXT("_%d"), DataType);
    
    // 覆盖写入（后提交的值为准，实现去重保留最新）
    FActorSnapshot& Snapshot = Bucket.Snapshots.FindOrAdd(MergeKey);
    Snapshot.ActorUID  = ActorUID;
    Snapshot.DataType  = DataType;
    Snapshot.Payload   = Payload; // 直接覆盖，不追加
}
```

### Step 3：Flush 帧桶为压缩数据包

```cpp
// 将所有已满的帧桶序列化 + 压缩后写入文件/网络
void FScenePlayBackSessionWriter::FlushBuckets(int64 CurrentTimestampMs)
{
    int64 CurrentBucket = AlignToFrameBucket(CurrentTimestampMs, FrameIntervalMs);
    
    TArray<int64> BucketsToFlush;
    for (auto& Pair : FrameBuckets)
    {
        // 只 Flush 比当前帧早的桶（当前帧可能还有数据未提交）
        if (Pair.Key < CurrentBucket)
            BucketsToFlush.Add(Pair.Key);
    }
    
    BucketsToFlush.Sort(); // 保证时序
    
    for (int64 BucketTime : BucketsToFlush)
    {
        FFrameBucket& Bucket = FrameBuckets[BucketTime];
        
        // 序列化帧数据
        TArray<uint8> FrameData = SerializeBucket(Bucket);
        
        // 压缩（选择 LZ4 或 zstd）
        TArray<uint8> Compressed = CompressFrame(FrameData);
        
        // 写入输出流（文件 / 网络）
        WriteCompressedFrame(Bucket.TimestampMs, Compressed);
        
        // 清理已处理的桶
        FrameBuckets.Remove(BucketTime);
    }
}
```

## 压缩策略选择

```cpp
enum class ECompressionMethod
{
    None,  // 调试用，无压缩
    LZ4,   // 速度优先，适合实时传输（压缩率约 2-3x）
    Zstd,  // 压缩率优先，适合离线存储（压缩率约 4-6x）
};

TArray<uint8> CompressFrame(const TArray<uint8>& Input, ECompressionMethod Method)
{
    switch (Method)
    {
    case ECompressionMethod::LZ4:
    {
        TArray<uint8> Output;
        // UE5 内置 LZ4
        FCompression::CompressMemory(NAME_LZ4, Output, Input.GetData(), Input.Num());
        return Output;
    }
    case ECompressionMethod::Zstd:
    {
        // 需要引入第三方 zstd 库
        // 或使用 UE5.2+ 内置 Oodle
        // ...
    }
    }
    return Input;
}
```

## Tick 驱动的 Flush 时机

```cpp
// 在 GameThread Tick 中定期 Flush
void UScenePlayBackLocalRecorderSubsystem::Tick(float DeltaTime)
{
    Super::Tick(DeltaTime);
    
    int64 NowMs = FDateTime::UtcNow().GetTicks() / ETimespan::TicksPerMillisecond;
    
    // 每帧检查是否有需要 Flush 的桶
    SessionWriter->FlushBuckets(NowMs);
}
```

## 性能数据参考

| 场景 | Actor 数 | 帧率 | 未压缩带宽 | LZ4 压缩后 |
|------|----------|------|-----------|-----------|
| 小场景 | 50       | 30fps | ~180KB/s  | ~60KB/s   |
| 中场景 | 200      | 30fps | ~720KB/s  | ~240KB/s  |
| 大场景 | 1000     | 30fps | ~3.6MB/s  | ~1.2MB/s  |

## 注意事项

1. **帧桶容量上限** — 如果 Actor 数量极大，单帧桶内存可能过高；可设置 `MaxSnapshotsPerBucket` 上限，超出时提前 Flush
2. **时钟同步** — 多机录制时，时间戳必须使用同步时钟（NTP），否则帧桶对齐会错位
3. **GameThread 安全** — `SubmitSnapshot` 通常从组件 Tick 调用（GameThread），`FlushBuckets` 也在 GameThread，无需加锁；若从 TaskGraph 线程提交，需要加 `FCriticalSection`
4. **Seek 后清空** — 回放 Seek 后应调用 `FrameBuckets.Empty()` 清空未 Flush 的桶，避免旧数据混入

## 来源项目

`ScenePlayBack` 插件 (`TestPlayBack` 项目) — `ScenePlayBackSessionWriter.h` + `ScenePlayBackCollect` 模块

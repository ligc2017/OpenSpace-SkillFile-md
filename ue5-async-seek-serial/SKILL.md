---
name: ue5-async-seek-serial
description: UE5 异步 Seek 防并发竞争 - SeekRequestSerial 原子递增模式，丢弃过期异步任务
tags: [ue5, unreal-engine, async, seek, playback, concurrency, atomic, c++]
---

# UE5 异步 Seek 防并发竞争

## 问题背景

回放系统中，用户快速拖动进度条会连续触发多个 Seek 请求。每次 Seek 都是一个异步操作（需要解压、加载帧数据）。如果不加保护：

- 多个 Seek 请求并发执行，最后完成的可能不是最新的请求
- 旧请求的结果覆盖新请求，导致画面跳回错误位置
- 严重时引发 Actor 状态撕裂（部分 Actor 在旧位置，部分在新位置）

## 解决方案：SeekRequestSerial 原子递增

核心思想：**每次 Seek 发出时递增一个序列号，异步任务完成时检查序列号，若不匹配则丢弃结果**。

```cpp
// PlayBackController.h
class UPlayBackController : public UActorComponent
{
    // 原子计数器 - 每次 Seek 递增
    std::atomic<int32> SeekRequestSerial{ 0 };

public:
    // 发起 Seek（可从 GameThread 任意时刻调用）
    void SeekToTime(float TimeSeconds);
};
```

## 完整实现

```cpp
// PlayBackController.cpp

void UPlayBackController::SeekToTime(float TimeSeconds)
{
    // Step 1: 递增序列号，拿到本次 Seek 的"票号"
    const int32 MySerial = ++SeekRequestSerial;

    // Step 2: 将 Seek 操作抛到异步线程（避免卡 GameThread）
    Async(EAsyncExecution::ThreadPool, [this, TimeSeconds, MySerial]()
    {
        // Step 3: 异步加载目标帧数据（可能耗时 10-100ms）
        TArray<FActorSnapshot> FrameData = LoadFrameAtTime(TimeSeconds);

        // Step 4: 回到 GameThread 应用结果
        AsyncTask(ENamedThreads::GameThread, [this, FrameData, MySerial, TimeSeconds]()
        {
            // Step 5: 关键检查！序列号不匹配 = 有更新的 Seek 已发出，丢弃本次结果
            if (SeekRequestSerial.load() != MySerial)
            {
                UE_LOG(LogPlayBack, Verbose,
                    TEXT("Seek to %.2f discarded (serial %d, current %d)"),
                    TimeSeconds, MySerial, SeekRequestSerial.load());
                return; // 直接返回，不应用任何状态变更
            }

            // Step 6: 序列号匹配，应用帧数据到 Actors
            ApplyFrameData(FrameData);
            CurrentPlaybackTime = TimeSeconds;
        });
    });
}
```

## 带加载状态的增强版本

```cpp
// 支持 UI 显示 "Seeking..." 状态

void UPlayBackController::SeekToTime(float TimeSeconds)
{
    const int32 MySerial = ++SeekRequestSerial;

    // 立即更新 UI 状态（在 GameThread）
    bIsSeeking = true;
    OnSeekStarted.Broadcast(TimeSeconds);

    Async(EAsyncExecution::ThreadPool, [this, TimeSeconds, MySerial]()
    {
        TArray<FActorSnapshot> FrameData = LoadFrameAtTime(TimeSeconds);

        AsyncTask(ENamedThreads::GameThread, [this, FrameData, MySerial, TimeSeconds]()
        {
            // 无论是否丢弃，检查是否是最后一个 Seek
            bool bIsLatest = (SeekRequestSerial.load() == MySerial);

            if (!bIsLatest)
            {
                // 不是最新 Seek，但如果这是当前仍在执行的最后一个，需要清除 Seeking 状态
                // 这里可以不做特殊处理，等最新 Seek 完成时自然清除
                return;
            }

            // 应用数据
            ApplyFrameData(FrameData);
            CurrentPlaybackTime = TimeSeconds;

            // 清除 Seeking 状态
            bIsSeeking = false;
            OnSeekCompleted.Broadcast(TimeSeconds);
        });
    });
}
```

## 与 TFuture / FGraphEvent 结合

```cpp
// 如果需要取消正在运行的异步任务（而不仅仅是丢弃结果），
// 可以结合 TFuture 的 cancel 机制：

class UPlayBackController : public UActorComponent
{
    std::atomic<int32> SeekRequestSerial{ 0 };
    
    // 存储当前 Seek 的 Future，用于判断是否可以取消
    TSharedPtr<TFuture<void>> CurrentSeekFuture;
};

void UPlayBackController::SeekToTime(float TimeSeconds)
{
    const int32 MySerial = ++SeekRequestSerial;
    
    // 将 Future 存起来（可以在下次 Seek 时决定是否取消）
    CurrentSeekFuture = MakeShared<TFuture<void>>(
        Async(EAsyncExecution::ThreadPool, [this, TimeSeconds, MySerial]()
        {
            // 在耗时操作的关键节点检查序列号（早期退出）
            if (SeekRequestSerial.load() != MySerial) return;

            TArray<FActorSnapshot> FrameData = LoadFrameAtTime_Part1(TimeSeconds);
            
            if (SeekRequestSerial.load() != MySerial) return; // 再次检查

            FrameData.Append(LoadFrameAtTime_Part2(TimeSeconds));

            AsyncTask(ENamedThreads::GameThread, [this, FrameData, MySerial, TimeSeconds]()
            {
                if (SeekRequestSerial.load() != MySerial) return;
                ApplyFrameData(FrameData);
            });
        })
    );
}
```

## 序列号溢出处理

```cpp
// int32 最大值约 21 亿，正常使用不会溢出
// 若担心极端情况，可以定期重置（在 PlayBack 停止时）

void UPlayBackController::StopPlayback()
{
    SeekRequestSerial.store(0); // 重置序列号
    bIsSeeking = false;
    // ...
}
```

## 注意事项

1. **`std::atomic<int32>` vs `TAtomic<int32>`** — UE5 推荐使用 `std::atomic`（C++17），性能与 `TAtomic` 相当，但标准兼容性更好
2. **GameThread 写入 `CurrentPlaybackTime`** — 如果其他线程需要读取 `CurrentPlaybackTime`，也应该原子化；若只在 GameThread 读写，`float` 即可
3. **序列号不是锁** — Serial 模式只是"丢弃旧结果"，**不能替代互斥锁**；如果多个线程同时写入共享状态，仍然需要 `FCriticalSection`
4. **异步线程数量** — `EAsyncExecution::ThreadPool` 用的是 UE 全局线程池；频繁 Seek 不会无限创建线程，会排队等待

## 来源项目

`ScenePlayBack` 插件 (`TestPlayBack` 项目) — `PlayBackController.h`

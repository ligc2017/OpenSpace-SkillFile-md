---
name: ue5-transform-pod-serialization
description: UE5 FTransform 跨平台 POD 序列化 - 用固定布局结构绕过 FTransform 内存不稳定问题
tags: [ue5, unreal-engine, serialization, transform, cross-platform, binary, c++]
---

# UE5 FTransform 跨平台 POD 序列化

## 问题背景

`FTransform` 在 UE5 中内部使用 `FQuat`（四元数）+ SIMD 对齐，其内存布局在不同编译器、平台、UE 版本间**不保证一致**：

- SIMD 对齐（`alignas(16)`）导致实际大小不固定
- 序列化 `FTransform` 到字节流后，在 Java/Web 端解析会因字段偏移错误而崩溃
- 不同 UE 版本间二进制兼容性无法保证

## 解决方案：固定布局 POD 结构

```cpp
#pragma pack(push, 1)

// 固定 40 字节，跨平台跨语言一致
struct FTransformPOD
{
    float Tx, Ty, Tz;        // Translation (12 bytes)
    float Rx, Ry, Rz, Rw;   // Rotation Quaternion (16 bytes)
    float Sx, Sy, Sz;        // Scale (12 bytes)
    // Total: 40 bytes
};

#pragma pack(pop)
```

## 转换函数

```cpp
// FTransform -> POD（录制时调用）
inline FTransformPOD ToTransformPOD(const FTransform& T)
{
    const FVector Loc   = T.GetLocation();
    const FQuat   Rot   = T.GetRotation();
    const FVector Scale = T.GetScale3D();

    FTransformPOD Pod;
    Pod.Tx = static_cast<float>(Loc.X);
    Pod.Ty = static_cast<float>(Loc.Y);
    Pod.Tz = static_cast<float>(Loc.Z);
    Pod.Rx = static_cast<float>(Rot.X);
    Pod.Ry = static_cast<float>(Rot.Y);
    Pod.Rz = static_cast<float>(Rot.Z);
    Pod.Rw = static_cast<float>(Rot.W);
    Pod.Sx = static_cast<float>(Scale.X);
    Pod.Sy = static_cast<float>(Scale.Y);
    Pod.Sz = static_cast<float>(Scale.Z);
    return Pod;
}

// POD -> FTransform（回放时调用）
inline FTransform FromTransformPOD(const FTransformPOD& Pod)
{
    return FTransform(
        FQuat(Pod.Rx, Pod.Ry, Pod.Rz, Pod.Rw),
        FVector(Pod.Tx, Pod.Ty, Pod.Tz),
        FVector(Pod.Sx, Pod.Sy, Pod.Sz)
    );
}
```

## 跨端布局对照表

| 字段   | 偏移 | 类型    | Java 类型 | JS 类型         |
|--------|------|---------|-----------|-----------------|
| Tx     | 0    | float32 | `float`   | `Float32`       |
| Ty     | 4    | float32 | `float`   | `Float32`       |
| Tz     | 8    | float32 | `float`   | `Float32`       |
| Rx     | 12   | float32 | `float`   | `Float32`       |
| Ry     | 16   | float32 | `float`   | `Float32`       |
| Rz     | 20   | float32 | `float`   | `Float32`       |
| Rw     | 24   | float32 | `float`   | `Float32`       |
| Sx     | 28   | float32 | `float`   | `Float32`       |
| Sy     | 32   | float32 | `float`   | `Float32`       |
| Sz     | 36   | float32 | `float`   | `Float32`       |

Java 解析示例：
```java
// ByteBuffer 默认 Big Endian，需切换为 Little Endian
ByteBuffer buf = ByteBuffer.wrap(data).order(ByteOrder.LITTLE_ENDIAN);
float tx = buf.getFloat(0);
float ty = buf.getFloat(4);
// ...
```

JavaScript 解析示例：
```javascript
const view = new DataView(buffer);
const tx = view.getFloat32(offset, true); // true = little-endian
const ty = view.getFloat32(offset + 4, true);
```

## 使用场景

```cpp
// 录制时：序列化到字节流
void RecordActorTransform(AActor* Actor, TArray<uint8>& OutStream)
{
    FTransformPOD Pod = ToTransformPOD(Actor->GetActorTransform());
    
    const int32 Offset = OutStream.AddUninitialized(sizeof(FTransformPOD));
    FMemory::Memcpy(OutStream.GetData() + Offset, &Pod, sizeof(FTransformPOD));
}

// 回放时：从字节流反序列化
void ApplyTransformFromStream(AActor* Actor, const uint8* Data)
{
    FTransformPOD Pod;
    FMemory::Memcpy(&Pod, Data, sizeof(FTransformPOD));
    Actor->SetActorTransform(FromTransformPOD(Pod));
}
```

## 注意事项

1. **四元数归一化** — 回放前调用 `FQuat.Normalize()` 防止浮点累积误差导致缩放异常
2. **坐标系差异** — UE5 使用左手坐标系，Y轴向右；Web 通常右手系，需要在端侧做坐标变换
3. **double 精度丢失** — UE5.1+ 默认启用 LargeWorldCoordinates（double），`static_cast<float>` 会丢失精度，大地图场景需评估是否改为 double POD
4. **Scale = (1,1,1) 优化** — 若 Scale 固定为单位缩放，可省略 12 字节，降低带宽（需要 SchemaId 区分）

## 来源项目

`ScenePlayBack` 插件 (`TestPlayBack` 项目) — `ScenePlayBackTypes.h` 中的 `FDirectorTransformPOD`

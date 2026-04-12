---
name: ue5-fnv1a-actor-uid
description: UE5 FNV-1a 64位 ActorUID 生成 - 基于(SchemaId, ActorID, DataType)三元组的确定性跨端一致 ID
tags: [ue5, unreal-engine, uid, hash, fnv1a, cross-platform, identification, c++]
---

# UE5 FNV-1a 64位 ActorUID 生成

## 适用场景

- 多端（UE5 / Web / Java / 服务端）需要用同一个 ID 唯一标识一个 Actor 的某类数据
- 录制/回放系统中，需要将 Actor 数据包与特定 Actor + 数据类型精确匹配
- 避免使用 `AActor::GetUniqueID()`（运行时不稳定，重启后变化）

## 核心算法：FNV-1a 64bit

FNV-1a（Fowler–Noll–Vo）是一种非加密哈希，特点：
- 速度极快（无乘法表查询）
- 确定性（相同输入永远相同输出）
- 跨平台一致（纯整数运算，无浮点/SIMD）

```cpp
// FNV-1a 64bit 常量
constexpr uint64 FNV_OFFSET_BASIS = 14695981039346656037ULL;
constexpr uint64 FNV_PRIME        = 1099511628211ULL;

// 核心哈希函数
inline uint64 FNV1a64(const uint8* Data, int32 Length)
{
    uint64 Hash = FNV_OFFSET_BASIS;
    for (int32 i = 0; i < Length; ++i)
    {
        Hash ^= static_cast<uint64>(Data[i]);
        Hash *= FNV_PRIME;
    }
    return Hash;
}
```

## 三元组 UID 生成

```cpp
// ActorUID 由 (SchemaId, ActorID, DataType) 三元组确定性生成
// 输出为 16 位十进制字符串（确保跨端 JSON/数据库兼容）

struct FActorUIDKey
{
    uint16 SchemaId;  // 数据结构类型（来自协议定义）
    uint32 ActorID;   // Actor 的稳定 ID（如关卡中的固定编号）
    uint8  DataType;  // 数据类型枚举（0=Transform, 1=AnimPose, ...）
};

FString GenerateActorUID(uint16 SchemaId, uint32 ActorID, uint8 DataType)
{
    // 将三元组打包为连续字节
    FActorUIDKey Key{ SchemaId, ActorID, DataType };
    
    // 计算 FNV-1a 64bit 哈希
    uint64 Hash = FNV1a64(reinterpret_cast<const uint8*>(&Key), sizeof(FActorUIDKey));
    
    // 转为 16 位十进制字符串（左补零）
    // 使用十进制而非十六进制，避免 Java Long 类型的符号位问题
    return FString::Printf(TEXT("%016llu"), Hash);
}
```

## 使用示例

```cpp
// 为 Actor 的 Transform 数据生成唯一 ID
FString TransformUID = GenerateActorUID(
    0x0001,       // SchemaId: Transform
    Actor->GetStableID(),  // ActorID: 关卡中预分配的稳定 ID
    0             // DataType: Transform = 0
);
// 输出示例："7894561230145678"

// 同一 Actor 的 AnimPose 数据会得到不同 UID
FString PoseUID = GenerateActorUID(0x0001, Actor->GetStableID(), 1);
// PoseUID != TransformUID，即使 ActorID 相同
```

## 跨端实现

**Java 实现：**
```java
private static final long FNV_OFFSET_BASIS = 0xcbf29ce484222325L; // 注意 Java long 是有符号的
private static final long FNV_PRIME = 0x00000100000001B3L;

public static String generateActorUID(short schemaId, int actorId, byte dataType) {
    ByteBuffer buf = ByteBuffer.allocate(7).order(ByteOrder.LITTLE_ENDIAN);
    buf.putShort(schemaId);
    buf.putInt(actorId);
    buf.put(dataType);
    
    long hash = FNV_OFFSET_BASIS;
    for (byte b : buf.array()) {
        hash ^= (b & 0xFFL);
        hash *= FNV_PRIME;
    }
    // 用 Long.toUnsignedString 避免符号位问题
    return String.format("%016s", Long.toUnsignedString(hash)).replace(' ', '0');
}
```

**JavaScript 实现：**
```javascript
// 注意：JS Number 精度不足，需要用 BigInt
const FNV_OFFSET = 14695981039346656037n;
const FNV_PRIME  = 1099511628211n;
const MASK64     = (1n << 64n) - 1n;

function generateActorUID(schemaId, actorId, dataType) {
    const buf = new ArrayBuffer(7);
    const view = new DataView(buf);
    view.setUint16(0, schemaId, true);  // little-endian
    view.setUint32(2, actorId, true);
    view.setUint8(6, dataType);
    
    let hash = FNV_OFFSET;
    const bytes = new Uint8Array(buf);
    for (const b of bytes) {
        hash ^= BigInt(b);
        hash = (hash * FNV_PRIME) & MASK64;
    }
    return hash.toString().padStart(16, '0');
}
```

## 注意事项

1. **ActorID 必须是稳定 ID** — 不能用 `AActor::GetUniqueID()`，需要在关卡设计时预分配固定整数 ID（如 DataAsset 或 DataTable 中定义）
2. **字节序一致** — 三元组打包时必须统一使用 Little Endian（`#pragma pack(1)` 结构体在 x86 上默认是 LE）
3. **碰撞概率** — FNV-1a 64bit 的碰撞概率约为 1/2^64，实际场景中可接受；若需要更高安全性，改用 xxHash64
4. **Java Long 有符号问题** — Java 的 `long` 是有符号 64bit，哈希值超过 `Long.MAX_VALUE` 时会变为负数，必须用 `Long.toUnsignedString()` 输出

## 来源项目

`ScenePlayBack` 插件 (`TestPlayBack` 项目) — `ActorUID.h`

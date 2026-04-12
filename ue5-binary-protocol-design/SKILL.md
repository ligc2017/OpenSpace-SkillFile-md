---
name: ue5-binary-protocol-design
description: UE5 二进制协议设计模式 - pragma pack(1) + Magic 字段版本控制 + PacketHeader 结构
tags: [ue5, unreal-engine, binary-protocol, serialization, network, c++]
---

# UE5 二进制协议设计

## 适用场景

- 需要跨 UE5/Web/Java 多端传输的二进制数据协议
- 录制/回放系统中的帧数据存储格式
- 需要版本兼容的网络包格式设计
- 高性能场景数据序列化（避免 JSON/文本开销）

## 技术栈

- Unreal Engine 5.3+
- C++ `#pragma pack(1)`
- 固定宽度整数类型（`uint8`, `uint16`, `uint32`, `int64`）

## 核心设计原则

### 1. 禁止内存对齐 Padding

```cpp
#pragma pack(push, 1)

struct FPacketHeader
{
    uint8  Magic;       // 魔数，用于校验包合法性
    uint8  Version;     // 协议版本号，V1=1, V2=2
    uint16 SchemaId;    // 数据结构类型标识
    uint32 PayloadSize; // Payload 字节数（不含 Header）
    int64  Timestamp;   // 时间戳（毫秒）
};

#pragma pack(pop)
```

> **关键**：`#pragma pack(1)` 确保结构体无 padding，使得 `sizeof(FPacketHeader)` 在所有平台和编译器上一致，跨端解析不会因对齐差异出错。

### 2. Magic 字段版本控制

```cpp
// 协议魔数常量 - 用于快速过滤非法数据包
constexpr uint8 PACKET_MAGIC_V1 = 0xA1;
constexpr uint8 PACKET_MAGIC_V2 = 0xA2;

// 解析时先检查 Magic
bool TryParsePacket(const uint8* Data, int32 DataLen, FPacketHeader& OutHeader)
{
    if (DataLen < sizeof(FPacketHeader))
        return false;

    FMemory::Memcpy(&OutHeader, Data, sizeof(FPacketHeader));

    if (OutHeader.Magic != PACKET_MAGIC_V1 && OutHeader.Magic != PACKET_MAGIC_V2)
        return false; // 非法包，丢弃

    return true;
}
```

### 3. SchemaId 驱动 Payload 解析

```cpp
// SchemaId 枚举 - 标识 Payload 中的数据类型
enum class EPacketSchema : uint16
{
    Transform      = 0x0001,  // Actor Transform 快照
    AnimPose       = 0x0002,  // 动画 Pose 数据
    CustomProperty = 0x0003,  // 自定义属性
    DirectorState  = 0x0100,  // 导调状态（V2 新增）
};

// 根据 SchemaId 分发解析
void DispatchPacket(const FPacketHeader& Header, const uint8* Payload)
{
    switch (static_cast<EPacketSchema>(Header.SchemaId))
    {
    case EPacketSchema::Transform:
        ParseTransformPayload(Payload, Header.PayloadSize);
        break;
    case EPacketSchema::DirectorState:
        if (Header.Magic == PACKET_MAGIC_V2) // V2 才支持
            ParseDirectorStatePayload(Payload, Header.PayloadSize);
        break;
    default:
        UE_LOG(LogPlayBack, Warning, TEXT("Unknown SchemaId: %d"), Header.SchemaId);
    }
}
```

## 版本兼容策略

| 策略 | 说明 |
|------|------|
| 新增字段 | 在 Payload 末尾追加，旧版客户端读取时忽略多余字节（PayloadSize 控制边界） |
| 不兼容变更 | 更新 Magic 值（V1→V2），旧版客户端收到 V2 包直接丢弃 |
| 字段重命名 | POD 结构只看偏移，不看名字，无需版本号 |

## 写入示例

```cpp
// 构建并写入一个 Transform 包
void WriteTransformPacket(TArray<uint8>& OutBuffer, uint16 SchemaId,
                          const FTransformPOD& TransformData, int64 TimestampMs)
{
    FPacketHeader Header;
    Header.Magic       = PACKET_MAGIC_V2;
    Header.Version     = 2;
    Header.SchemaId    = SchemaId;
    Header.PayloadSize = sizeof(FTransformPOD);
    Header.Timestamp   = TimestampMs;

    const int32 TotalSize = sizeof(FPacketHeader) + sizeof(FTransformPOD);
    OutBuffer.SetNumUninitialized(TotalSize);

    FMemory::Memcpy(OutBuffer.GetData(), &Header, sizeof(FPacketHeader));
    FMemory::Memcpy(OutBuffer.GetData() + sizeof(FPacketHeader),
                    &TransformData, sizeof(FTransformPOD));
}
```

## 注意事项

1. **不要用 `FArchive` 序列化 POD 结构** — `FArchive` 会加入额外的版本信息字节，破坏跨端兼容性
2. **所有 POD 字段必须使用固定宽度类型** — 禁止 `int`/`long`/`float` 等平台相关类型，用 `int32`/`int64`/`float`（UE float = IEEE 754 32bit，跨平台一致）
3. **Big/Little Endian** — UE5 在 PC/Console 上均为 Little Endian，Web/Java 端需要注意字节序转换
4. **`#pragma pack` 配对使用** — 必须 `push` + `pop`，避免影响后续结构体的对齐

## 来源项目

`ScenePlayBack` 插件 (`TestPlayBack` 项目) — `ScenePlayBackTypes.h`

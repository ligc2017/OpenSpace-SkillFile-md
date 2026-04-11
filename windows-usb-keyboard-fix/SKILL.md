---
name: windows-usb-keyboard-fix
description: 诊断并修复 Windows 11 开机后 USB 键盘无法识别、需要重新拔插才生效的问题
tags: [windows, usb, keyboard, hardware, troubleshooting, powershell]
---

# Windows 11 USB 键盘开机无法识别修复技能

## 适用场景
Windows 11 开机后键盘无法使用，必须重新拔插 USB 才能正常识别。

## 根本原因
通常是以下一种或多种：
1. **快速启动（Fast Boot）** - 跳过完整初始化，USB 控制器未重置
2. **USB 选择性暂停** - 电源管理挂起 USB 设备
3. **残留设备驱动** - 历史 HID 键盘设备注册信息冲突
4. **USB 控制器驱动问题** - 需要更新驱动

## 诊断命令（PowerShell）

```powershell
# 查看所有 HID 键盘设备（包含隐藏/Unknown 设备）
Get-PnpDevice -Class Keyboard | Select-Object Status, FriendlyName, InstanceId

# 查看 USB 控制器状态
Get-PnpDevice -Class USB | Where-Object {$_.Status -ne 'OK'}
```

## 修复方案（按优先级）

### 方案1：禁用 USB 选择性暂停（最常见，立即生效）
```
控制面板 → 电源选项 → 更改计划设置
→ 更改高级电源设置 → USB 设置
→ USB 选择性暂停设置 → 禁用
```

### 方案2：清除残留 HID 设备驱动
```
设备管理器 → 查看 → 显示隐藏的设备
→ 人体学输入设备 → 右键卸载所有 "Unknown" 状态设备
```

PowerShell 批量卸载：
```powershell
Get-PnpDevice -Class Keyboard | Where-Object {$_.Status -eq 'Unknown'} | ForEach-Object {
    & pnputil /remove-device $_.InstanceId
}
```

### 方案3：关闭 Windows 快速启动（最根本解决）
```
控制面板 → 电源选项 → 选择电源按钮的功能
→ 启用快速启动 → 取消勾选 → 保存更改
```

### 方案4：更新 USB 控制器驱动
```
设备管理器 → 通用串行总线控制器
→ 右键每个控制器 → 更新驱动程序
```

### 方案5：更新 BIOS 固件
- 前往主板厂商官网，检索是否有 USB 初始化相关的 BIOS 更新

## 推荐执行顺序
1. 先执行方案3（关闭快速启动）→ 重启验证
2. 若无效，执行方案1（禁用 USB 暂停）→ 重启验证
3. 若无效，执行方案2（清理残留驱动）→ 重启验证
4. 方案4、5 作为最后手段

## 注意事项
- 关闭快速启动后，每次开机会慢几秒，但 USB 初始化更稳定
- 方案2 执行后，Windows 会在下次连接时自动重新安装正确驱动

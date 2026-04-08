# CleanDesk

一个专注于 **Windows 桌面/下载文件自动整理** 的轻量工具。  
基于文件系统事件（watchdog）实时归类，并提供 **撤销、暂停、dry-run** 等安全机制。

## 功能亮点
- 默认监听 `Desktop` 和 `Downloads`（也支持多文件夹监听）
- 按扩展名自动归类到目标文件夹
- 文件占用检测 + 稳定性检查，避免“写入中就移动”
- **占位命名延迟**（如“新建/未命名/New/Untitled”）避免重命名被打断
- **Undo 最近移动**（托盘一键撤销）
- **dry-run 模式**：只记录将要移动的操作，不真正移动
- 可选 **日期子目录**（如 `Images/2026-04/`）
- 启动时扫描一次，补处理离线创建的文件
- 托盘控制：暂停、退出、通知开关、dry-run 开关、开机启动

## 系统要求
- Windows 10/11
- Python 3.11+（开发环境）

## 快速启动（开发模式）
```powershell
uv run python -m cleandesk
```

## 配置说明
当前配置来源于内置规则文件：  
`C:\Users\zhang\Marco\CleanDesk\cleandesk\resources\default_rules.json`

你可以在该文件中调整：
- `rules`：扩展名 → 目标文件夹
- `exclude_dirs`：排除目录
- `watch_dirs`：多文件夹监听（为空则默认 Desktop/Downloads）
- `notifications.enabled`：通知开关（默认关闭）
- `date_subfolders.enabled` / `date_subfolders.folders`：日期分类
- `dry_run.enabled`：dry-run 模式

## 托盘功能
启动后会出现托盘图标，支持：
- 暂停/继续
- Undo 最近移动
- 通知开关
- dry-run 开关
- 开机启动开关
- 退出

## 测试
```powershell
uv run python -m pytest
```

## 打包构建（PyInstaller）
```powershell
./scripts/build.ps1
```
输出：`C:\Users\zhang\Marco\CleanDesk\dist\CleanDesk.exe`

## 生成安装包（NSIS）
需要先安装 NSIS，然后执行：
```powershell
./scripts/build.ps1 -Installer
```
输出：`C:\Users\zhang\Marco\CleanDesk\dist\CleanDesk_Setup.exe`

## 免责声明
本工具会自动移动文件。  
请先在 **dry-run** 模式下验证规则，再开启真实移动，以避免误移动重要文件。

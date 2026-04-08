基于你提供的《CleanDesk 项目总览 v0.1.0》，可以将开发过程形式化为一个**工程化可执行路线（Engineering Roadmap）**。我会按**阶段 → 子任务 → 输出物 → 技术要点 → 验收标准**的方式展开，确保它不仅是“计划”，而是可以直接执行的开发规范。

---

# 一、总体开发策略（关键原则）

你的项目本质是一个：

> **基于文件系统事件的实时处理系统（event-driven system）**

因此必须遵循三个工程原则：

### 1. 解耦（Decoupling）

Watcher / Engine / Mover 必须严格分离（你文档中已正确设计）

### 2. 异步与线程安全

- watchdog → IO线程
- worker → 处理线程
- UI → 主线程

### 3. 可回滚（Reversibility）

- undo buffer 是核心可信机制（降低用户心理阻力）

---

# 二、开发路线（阶段化 Step-by-Step）

## 阶段 0：环境与脚手架（M0）

### Step 0.1 项目初始化

**任务**

- 初始化项目结构（严格按文档）
- 创建 `pyproject.toml`

**技术要点**

- 推荐用：
    - `uv` 或 `poetry`
- Python 版本锁定 3.11+

**输出**

cleandesk/  
  main.py  
  config.py  
  ...

**验收标准**

- `python -m cleandesk` 可运行空程序

---

### Step 0.2 基础依赖安装

**核心依赖**

pip install watchdog pydantic rich pystray pillow plyer pytest

---

### Step 0.3 日志系统（logger.py）

**任务**

- 初始化 logging + Rich

**关键点**

- 分级日志：
    - DEBUG（开发）
    - INFO（用户）
    - ERROR（异常）

**验收**

- 控制台输出结构化日志

---

## 阶段 1：文件监听系统（M1）

## Step 1.1 watcher.py 实现

**核心目标**  
封装 watchdog → 产生统一事件流

**接口设计（建议）**

class FileEvent:  
    path: Path  
    event_type: str  # created / modified

**关键实现**

- 使用 `Observer`
- 监听：
    - Desktop
    - Downloads

---

## Step 1.2 事件队列

**任务**

- 建立线程安全队列

from queue import Queue  
  
event_queue = Queue()

---

## Step 1.3 过滤噪声事件

**必须处理**

- 临时文件（.tmp）
- 系统文件
- 重复触发（watchdog 常见问题）

---

**验收标准**

- 新建文件时，控制台能打印事件

---

## 阶段 2：规则引擎（M2）

## Step 2.1 config.py（配置系统）

**任务**

- 加载 JSON
- 使用 Pydantic 校验

**示例结构**

{  
  "rules": {  
    ".pdf": "Documents",  
    ".jpg": "Images"  
  }  
}

---

## Step 2.2 engine.py（分类逻辑）

**核心函数**

def classify(path: Path) -> str:

**逻辑**

1. 提取扩展名
2. 查规则表
3. fallback → Others

---

## Step 2.3 单元测试

使用 `pytest`

测试：

- 正确分类
- 未知类型

---

**验收标准**

- 输入文件路径 → 返回正确分类

---

## 阶段 3：文件移动系统（M3核心）

## Step 3.1 mover.py

这是**最关键模块（系统稳定性核心）**

---

### Step 3.1.1 稳定性延迟

time.sleep(1.5)

或更严谨：

- 检查文件 size 是否稳定

---

### Step 3.1.2 文件占用检测

with open(file, 'rb'):  
    pass

失败 → retry

---

### Step 3.1.3 冲突处理

file.txt → file (2026-04-07).txt

---

### Step 3.1.4 安全移动

shutil.move(src, dst)

---

## Step 3.2 Undo Buffer（关键差异化功能）

**数据结构**

deque(maxlen=50)

存储：

(src, dst)

---

**验收标准**

- 文件被正确移动
- 无覆盖
- 可回滚

---

## 阶段 4：端到端整合（MVP完成）

## Step 4.1 engine + mover + watcher 串联

流程：

watcher → queue → worker → engine → mover

---

## Step 4.2 worker线程

while True:  
    event = queue.get()  
    process(event)

---

**验收标准（关键）**

- 新文件 → 自动分类 → 成功移动

---

# 三、v0.2 扩展（系统级功能）

## Step 5.1 托盘 UI（pystray）

功能：

- 状态显示
- 暂停
- 退出
- undo

---

## Step 5.2 通知系统（plyer）

触发：

- 文件被移动时

---

## Step 5.3 开机启动

注册表：

HKCU\Software\Microsoft\Windows\CurrentVersion\Run

---

# 四、v0.3 增强（产品化能力）

重点模块：

### 1. 多文件夹监听

→ watcher 支持 list

### 2. 日期分类

Images/2026-04/

### 3. dry-run

不执行 move，仅 log

---

# 五、v1.0 发布（工程化）

## Step 6.1 打包（PyInstaller）

pyinstaller --onefile main.py

---

## Step 6.2 安装器（NSIS）

生成：

CleanDesk_Setup.exe

---

## Step 6.3 分发

- GitHub Releases
- 官网
- winget

---

# 六、关键技术难点（必须重点处理）

## 1. watchdog 重复事件

解决：

- debounce（时间窗口去重）

---

## 2. 文件未写完

解决：

- size稳定检测（优于 sleep）

---

## 3. 用户误操作风险

解决：

- undo buffer（必须稳定）

---

## 4. 多线程问题

解决：

- queue + 无共享状态

---

# 七、推荐开发节奏（现实可执行）

|周|目标|
|---|---|
|第1周|脚手架 + watcher|
|第2周|engine|
|第3周|mover|
|第4周|MVP跑通|
|第5周|tray|
|第6周|打包|
|第7-8周|测试 + 发布|

---

# 八、关键建议（工程视角）

## 1. Python 是正确选择

原因：

- watchdog（Windows API封装成熟）
- 快速迭代能力远强于 C++
- 分发问题可通过 PyInstaller解决（文档已考虑）

---

## 2. MVP必须极简

不要一开始做：

- GUI
- 复杂规则
- 多文件夹

---

## 3. 核心成功标准

不是功能多，而是：

> **“文件落地 → 无错误自动归类” 的成功率 > 99.9%**
# 嵌入真实终端方案对比

## 当前问题
WinConsole 自己实现的终端缺少完整的 VT100/xterm 支持，导致 TUI 程序无法正常工作。

## 解决方案：嵌入真实的终端模拟器

---

## 方案 1: 嵌入 Windows ConHost/ConPTY ⭐ 推荐

### 原理
使用 Windows 的 ConPTY (Console Pseudo-Terminal) API，这是 Windows Terminal 底层使用的技术。

### 优点
- ✅ 原生 Windows 支持
- ✅ 完整的 Windows Console API 支持
- ✅ 所有 TUI 程序都能正常工作
- ✅ 不需要额外依赖
- ✅ 性能最好

### 缺点
- ⚠️ 需要使用 Win32 API
- ⚠️ 只支持 Windows 10 1809+
- ⚠️ 实现相对复杂

### 实现方式
```python
# 使用 pywinpty 或直接调用 ConPTY API
# 1. 创建 ConPTY 实例
# 2. 将 PTY 输出渲染到 Qt widget
# 3. 转发键盘输入到 PTY
```

### 工作量
- 中等（2-3天）
- 主要是 Win32 API 调用和 Qt 集成

---

## 方案 2: 嵌入 pyte（VT100 模拟器）⭐⭐ 最易实现

### 原理
使用 pyte 库（纯 Python 的 VT100 终端模拟器）+ 改进的渲染层。

### 优点
- ✅ 纯 Python 实现，易于集成
- ✅ 完整的 VT100/ANSI 支持
- ✅ 跨平台（Windows/Linux/macOS）
- ✅ 可以保留现有代码结构
- ✅ 支持所有 TUI 程序

### 缺点
- ⚠️ 性能略低于原生方案
- ⚠️ 需要正确处理所有转义序列

### 实现方式
```python
import pyte

# 创建虚拟终端
screen = pyte.Screen(80, 24)
stream = pyte.Stream(screen)

# 处理输出
stream.feed(data_from_backend)

# 渲染到 Qt widget
for line in screen.display:
    render_line(line)
```

### 工作量
- 较小（1-2天）
- 主要是替换现有的 ANSI 解析逻辑

---

## 方案 3: 嵌入 xterm.js（Web 终端）

### 原理
使用 QWebEngineView 嵌入 xterm.js（JavaScript 终端模拟器）。

### 优点
- ✅ 非常成熟的终端模拟器
- ✅ 完整的 VT100/xterm 支持
- ✅ 美观的渲染效果
- ✅ 主题丰富

### 缺点
- ⚠️ 需要安装 PyQt6-WebEngine
- ⚠️ 内存占用较高（每个终端一个 WebView）
- ⚠️ 需要 JavaScript 和 Python 通信

### 实现方式
```python
from PyQt6.QtWebEngineWidgets import QWebEngineView

# 创建 WebView
web_view = QWebEngineView()
web_view.setHtml(xterm_html)

# 通过 WebChannel 通信
# Python -> JS: 发送终端输出
# JS -> Python: 接收用户输入
```

### 工作量
- 中等（2-3天）
- 需要设置 WebChannel 和 JavaScript 通信

---

## 方案 4: 嵌入 Windows Terminal 窗口

### 原理
使用 Win32 API 将 Windows Terminal 的窗口作为子窗口嵌入到 Qt widget。

### 优点
- ✅ 使用真正的 Windows Terminal
- ✅ 100% 兼容所有程序
- ✅ 原生外观

### 缺点
- ⚠️ 实现复杂（窗口嵌入）
- ⚠️ 可能有窗口焦点问题
- ⚠️ Windows Terminal 必须安装
- ⚠️ 难以控制窗口生命周期

### 实现方式
```python
# 使用 Win32 API
# 1. 启动 Windows Terminal 进程
# 2. 获取窗口句柄（FindWindow）
# 3. 设置为子窗口（SetParent）
# 4. 调整窗口大小和位置
```

### 工作量
- 较大（3-5天）
- Win32 API 调用和窗口管理复杂

---

## 推荐方案排序

### 1. **方案 2: pyte** ⭐⭐⭐ 最推荐
- **工作量小**，1-2天即可完成
- **代码改动最少**，保留现有架构
- **跨平台**，未来可以支持 Linux
- **效果好**，完整的 VT100 支持

### 2. **方案 1: ConPTY**
- Windows 原生方案
- 性能最好
- 但实现稍复杂

### 3. **方案 3: xterm.js**
- 成熟可靠
- 但需要 WebEngine（依赖较重）

### 4. **方案 4: 嵌入 Windows Terminal**
- 最复杂
- 不推荐

---

## 具体实施建议

### 如果选择 pyte（推荐）：

#### 步骤 1: 安装 pyte
```bash
pip install pyte
```

#### 步骤 2: 修改 terminal_widget.py
```python
import pyte

class TerminalWidget:
    def __init__(self):
        # 创建虚拟终端
        self.screen = pyte.Screen(80, 24)
        self.stream = pyte.Stream(self.screen)

    def _handle_output(self, data: str):
        # 让 pyte 处理所有输出
        self.stream.feed(data)

        # 渲染屏幕
        self._render_screen()

    def _render_screen(self):
        # 清空显示
        self.output_view.clear()

        # 逐行渲染
        for y, line in enumerate(self.screen.display):
            # 获取该行的字符和属性
            for x, char in enumerate(line):
                cell = self.screen.buffer[y][x]
                # 根据 cell.fg, cell.bg, cell.bold 等属性渲染
                self._render_cell(char, cell)
```

#### 步骤 3: 处理用户输入
```python
def _handle_input(self, key_event):
    # pyte 会自动处理光标移动等
    # 我们只需要发送按键到后端
    self.backend.send(key_data)
```

#### 优点：
- 所有 TUI 程序的菜单、光标移动、颜色都能正常工作
- 不需要自己解析 ANSI 序列
- pyte 内置了完整的 VT100 状态机

---

## 快速验证

### 测试 pyte 是否满足需求：

```python
import pyte

# 创建终端
screen = pyte.Screen(80, 24)
stream = pyte.Stream(screen)

# 模拟 codex 的菜单输出
menu_output = "\x1b[2J\x1b[H\x1b[1mMenu:\x1b[0m\n"
menu_output += "\x1b[32m1. Option 1\x1b[0m\n"
menu_output += "\x1b[32m2. Option 2\x1b[0m\n"
menu_output += "\x1b[7m> Select:\x1b[27m"

stream.feed(menu_output)

# 查看渲染结果
for line in screen.display:
    print(repr(line))

# 检查光标位置
print(f"Cursor: {screen.cursor.x}, {screen.cursor.y}")
```

---

## 时间估算

- **方案 2 (pyte)**: 1-2天
  - 0.5天：集成 pyte 库
  - 0.5天：实现渲染逻辑
  - 0.5天：测试和调试

- **方案 1 (ConPTY)**: 2-3天
  - 1天：学习 ConPTY API
  - 1天：实现集成
  - 1天：测试和调试

---

## 建议

**立即开始：方案 2 (pyte)**

原因：
1. 最快速（1-2天）
2. 最简单（纯 Python）
3. 最可靠（成熟库）
4. 效果最好（完整 VT100 支持）

如果 pyte 效果不理想，再考虑 ConPTY 方案。

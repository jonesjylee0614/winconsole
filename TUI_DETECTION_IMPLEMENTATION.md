# TUI 程序检测与外部终端启动 - 实现说明

## 概述

实现了智能 TUI (文本用户界面) 程序检测功能，当用户尝试在 WinConsole 中运行需要完整终端仿真支持的程序（如 codex、vim、htop）时，会自动提示并提供在外部终端中打开的选项。

## 实现的功能

### 1. TUI 程序检测

**文件**: `winconsole/constants.py`

定义了需要完整终端支持的 TUI 程序列表：

```python
TUI_PROGRAMS = {
    # AI 编码助手
    'codex', 'claude', 'aider', 'cursor',

    # 编辑器
    'vim', 'nvim', 'neovim', 'vi', 'nano', 'emacs', 'micro',

    # 系统监控
    'htop', 'top', 'btop', 'gotop', 'ytop', 'glances',

    # 文件管理器
    'mc', 'ranger', 'nnn', 'lf', 'vifm',

    # 其他 TUI 工具
    'tmux', 'screen', 'weechat', 'irssi', 'mutt', 'lynx', 'w3m',
    'tig', 'lazygit', 'gitui', 'ncdu', 'cmus', 'ncmpcpp',
}
```

**文件**: `winconsole/utils.py` (行 143-161)

实现了智能检测函数：

```python
def is_tui_program(cmd: str) -> bool:
    """检查命令是否是 TUI 程序

    特性:
    - 提取程序名称（去除路径）
    - 大小写不敏感
    - 自动处理 .exe 扩展名
    """
```

### 2. 外部终端启动

**文件**: `winconsole/utils.py` (行 164-204)

实现了在外部终端中打开命令的功能：

```python
def open_in_external_terminal(cmd: str, args: list[str], cwd: str) -> bool:
    """在外部终端中打开命令

    优先级:
    1. Windows Terminal (wt.exe) - 推荐
    2. cmd.exe - 后备方案

    返回: True 如果成功启动
    """
```

### 3. 动态命令拦截

**文件**: `winconsole/main_window.py`

#### 3.1 会话级别检测 (行 138-146, 217-220)

当创建会话时，如果检测到会话的命令本身是 TUI 程序：
- 在顶部显示橙色的 "在外部终端打开" 按钮
- 显示警告信息

#### 3.2 命令级别检测 (行 346-423)

`_handle_pre_send()` 方法拦截用户输入的命令：

```python
def _handle_pre_send(self, text: str) -> bool:
    """命令预处理

    流程:
    1. 检测是否是 TUI 程序
    2. 如果是，弹出对话框询问用户
    3. 用户选择 "是" -> 在外部终端启动，不发送到当前终端
    4. 用户选择 "否" -> 显示警告，继续在当前终端运行
    """
```

**交互对话框**:
- 明确告知用户 TUI 程序的限制
- 提供两个选项：外部终端 / 当前窗口
- 默认选择外部终端（更安全）

#### 3.3 智能命令构造 (行 375-394)

根据当前 shell 类型构造正确的外部终端命令：

- **WSL**: `wsl -- bash -c "codex"`
- **Bash**: `bash -c "codex"`
- **PowerShell**: `powershell -Command "codex"`
- **CMD**: `cmd /c "codex"`
- **其他**: 直接运行命令

### 4. 警告消息

**文件**: `winconsole/main_window.py` (行 382-403)

两种警告方式：

1. **`_show_tui_warning()`**: 会话创建时的完整警告
2. **`_warn_tui_command()`**: 命令执行时的简洁警告

## 用户体验流程

### 场景 1: 在 WSL 中输入 codex

1. 用户在 WSL 会话中输入 `codex` 并按回车
2. WinConsole 检测到 "codex" 是 TUI 程序
3. 弹出对话框：
   ```
   ⚠️ 检测到 TUI 程序: codex

   此程序需要完整的终端模拟器支持（VT100/xterm），
   在 WinConsole 中可能无法正常工作（菜单不显示、输入异常等）。

   是否在外部终端（Windows Terminal）中打开？

   • 选择"是"：在 Windows Terminal 中运行 codex
   • 选择"否"：在当前窗口尝试运行（可能有问题）
   ```
4. 用户选择 "是"：
   - 启动 Windows Terminal 执行 `wsl -- bash -c "codex"`
   - 在 WinConsole 中显示: `✓ 已在外部终端启动: codex`
5. 用户选择 "否"：
   - 显示警告消息
   - 继续在当前终端执行（可能有问题）

### 场景 2: 创建 vim 会话

1. 用户创建一个直接运行 vim 的会话
2. 会话创建时检测到 cmd 是 "vim"
3. 顶部出现橙色按钮 "在外部终端打开"
4. 显示完整警告消息
5. 用户点击按钮，在 Windows Terminal 中打开 vim

## 测试

### 单元测试

运行测试脚本验证检测逻辑：

```bash
python test_tui_detection.py
```

测试覆盖：
- ✓ 常见 TUI 程序识别
- ✓ 常规命令不误报
- ✓ .exe 扩展名处理
- ✓ 大小写不敏感
- ✓ 完整路径处理

### 集成测试

1. **测试 WSL 中的 codex**:
   ```
   - 启动 WinConsole
   - 创建 WSL 会话
   - 输入 "codex"
   - 验证弹出对话框
   - 选择 "是"，验证 Windows Terminal 启动
   ```

2. **测试 vim 直接会话**:
   ```
   - 创建 vim 会话
   - 验证橙色按钮显示
   - 验证警告消息显示
   - 点击按钮，验证外部终端启动
   ```

3. **测试普通命令不受影响**:
   ```
   - 输入 "ls"、"git status" 等
   - 验证不弹出对话框
   - 验证正常执行
   ```

## 技术细节

### 关键文件修改

1. **winconsole/constants.py**:
   - 添加 `TUI_PROGRAMS` 集合

2. **winconsole/utils.py**:
   - `is_tui_program()`: TUI 检测
   - `open_in_external_terminal()`: 外部终端启动

3. **winconsole/main_window.py**:
   - `_handle_pre_send()`: 命令拦截与处理
   - `_warn_tui_command()`: 运行时警告
   - `_show_tui_warning()`: 会话级警告
   - `_handle_open_external()`: 外部终端启动处理

### 设计决策

1. **两级检测**:
   - 会话级: 检测 session.cmd
   - 命令级: 检测用户输入的命令

2. **用户选择权**:
   - 不强制拦截，用户可以选择继续尝试
   - 默认推荐外部终端（更安全）

3. **智能命令构造**:
   - 根据当前 shell 类型自动构造正确的启动命令
   - 保持工作目录一致性

4. **清晰的用户反馈**:
   - 对话框明确说明问题和选项
   - 执行后显示结果消息
   - 失败时提供手动操作建议

## 已知限制

1. **依赖 Windows Terminal**:
   - 优先使用 wt.exe
   - 后备使用 cmd.exe（用户体验较差）

2. **TUI 程序列表**:
   - 需要手动维护
   - 可能有遗漏（用户可以提交 PR 添加）

3. **命令参数**:
   - 简单的命令检测（只检查第一个 token）
   - 不处理管道、重定向等复杂情况

## 未来改进

1. **用户自定义 TUI 列表**:
   - 允许在配置文件中添加/移除程序

2. **记住用户选择**:
   - "不再询问" 选项
   - 保存到配置文件

3. **更智能的检测**:
   - 检测程序是否尝试使用 raw mode
   - 检测 ANSI escape 序列密度

4. **其他外部终端支持**:
   - Alacritty
   - iTerm2 (macOS)
   - GNOME Terminal (Linux)

## 总结

此实现提供了一个用户友好的解决方案来处理 TUI 程序在 WinConsole 中的兼容性问题。通过智能检测和清晰的用户交互，确保用户能够在正确的环境中运行需要完整终端支持的程序，同时保持 WinConsole 作为轻量级进程管理器的核心定位。

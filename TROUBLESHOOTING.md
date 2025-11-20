# WinConsole 故障排除指南

## 常见问题

### 1. "系统找不到指定的文件" 错误（WSL/ERROR_FILE_NOT_FOUND）

#### 症状
当尝试在外部终端运行 TUI 程序（如 codex）时，出现：
```
系统找不到指定的文件。
错误代码: Wsl/ERROR_FILE_NOT_FOUND
[已退出进程，代码为 4294967295 (0xffffffff)]
```

#### 原因
这个错误表示 WSL 无法找到你尝试运行的命令。可能的原因：

1. **命令不在 PATH 中**
   - codex 可能需要在特定的 conda 环境中才能使用
   - 命令可能安装在非标准路径

2. **环境未激活**
   - 如果 codex 安装在 conda 环境中，需要先激活环境
   - bash -l -c "codex" 不会自动激活 conda 环境

3. **命令拼写错误或未安装**
   - 检查命令是否正确拼写
   - 使用 `which codex` 或 `command -v codex` 检查命令是否存在

#### 解决方案

**方案 A: 使用 "打开交互式 Shell" 选项（推荐）**

1. 当检测到 TUI 程序时，选择 **"打开交互式 Shell"** 而不是 "运行 codex"
2. 在打开的 Windows Terminal 中：
   ```bash
   # 如果需要，先激活 conda 环境
   conda activate your_env_name

   # 然后运行命令
   codex
   ```

**方案 B: 修改命令以包含环境激活**

如果你经常需要运行需要特定环境的命令，可以：

1. 在 WSL 的 ~/.bashrc 中添加：
   ```bash
   # 自动激活默认 conda 环境
   conda activate base  # 或你的默认环境名
   ```

2. 或者创建一个别名：
   ```bash
   # 在 ~/.bashrc 中添加
   alias codex='conda run -n your_env_name codex'
   ```

**方案 C: 直接在 WinConsole 中手动操作**

1. 在 WinConsole 的 WSL 会话中先激活环境：
   ```bash
   conda activate your_env_name
   ```

2. 然后运行命令：
   ```bash
   codex
   ```

3. 选择 "仍在此处尝试" 选项

#### 检查命令是否可用

在 WSL 中运行以下命令检查：

```bash
# 检查 codex 是否在 PATH 中
which codex

# 或
command -v codex

# 如果没有输出，说明命令不在 PATH 中
# 检查是否在 conda 环境中
conda list | grep codex

# 查看 conda 环境列表
conda env list
```

### 2. Windows Terminal 打开多个窗口或重复错误

#### 症状
点击 "运行 codex" 后，Windows Terminal 打开了多个窗口，或显示重复的错误消息。

#### 原因
- 命令执行失败后 Windows Terminal 可能会保持窗口打开
- 如果使用了 `/k` 参数（保持窗口打开），错误会一直显示

#### 解决方案
1. 关闭所有打开的 Windows Terminal 窗口
2. 下次选择 "打开交互式 Shell" 选项
3. 在交互式 shell 中手动运行和调试命令

### 3. TUI 程序在 WinConsole 中显示异常

#### 症状
- 菜单不显示或无法选择
- 看到乱码如 `[>7u`, `[?2004h` 等
- 方向键不工作
- 输入被重复显示

#### 原因
WinConsole 是一个轻量级进程管理器，不是完整的终端模拟器。缺少：
- 完整的 VT100/xterm 序列支持
- Raw mode 支持
- 高级 ANSI 转义序列处理

#### 解决方案
**始终在外部终端运行 TUI 程序**：
- vim, nvim, nano, emacs
- htop, btop, top
- ranger, mc
- tmux, screen
- codex, aider, cursor
- lazygit, tig

### 4. 日志查看

如果问题持续存在，查看日志文件获取更多信息：

**日志位置**:
```
~/.winconsole/logs/winconsole.log
```

**Windows 路径**:
```
C:\Users\你的用户名\.winconsole\logs\winconsole.log
```

**查看日志**:
```bash
# 在 WSL 中
tail -f ~/.winconsole/logs/winconsole.log

# 或在 Windows 中用记事本打开
notepad C:\Users\你的用户名\.winconsole\logs\winconsole.log
```

日志中会包含：
- 启动外部终端的完整命令
- 任何错误消息
- 执行状态

## 推荐的工作流程

### 对于需要 conda 环境的命令

1. **启动时激活环境**（推荐）
   ```bash
   # 在 ~/.bashrc 末尾添加
   if [[ -z "$CONDA_DEFAULT_ENV" ]]; then
       conda activate your_default_env
   fi
   ```

2. **或使用 conda run**
   ```bash
   conda run -n your_env_name codex
   ```

### 对于 TUI 程序

**不要在 WinConsole 中运行**，始终使用外部终端：
1. 检测到 TUI 程序时，选择 "打开交互式 Shell"
2. 在 Windows Terminal 中手动运行命令
3. 这样可以看到完整的错误信息和正常的 TUI 界面

### 对于普通命令行工具

可以安全地在 WinConsole 中运行：
- git, ls, cd, cat, grep 等
- python scripts
- npm, pip 命令
- 大多数非交互式命令

## 测试你的环境

创建一个测试脚本来检查环境：

```bash
# 保存为 test_env.sh
#!/bin/bash

echo "=== Environment Test ==="
echo "Current directory: $(pwd)"
echo "PATH: $PATH"
echo ""

echo "=== Conda Status ==="
if command -v conda &> /dev/null; then
    echo "Conda found: $(which conda)"
    echo "Active environment: $CONDA_DEFAULT_ENV"
    conda env list
else
    echo "Conda not found"
fi
echo ""

echo "=== Command Availability ==="
commands=("codex" "vim" "git" "python")
for cmd in "${commands[@]}"; do
    if command -v "$cmd" &> /dev/null; then
        echo "✓ $cmd: $(which $cmd)"
    else
        echo "✗ $cmd: not found"
    fi
done
```

运行：
```bash
chmod +x test_env.sh
./test_env.sh
```

## 获取帮助

如果问题仍未解决：

1. **查看完整日志**
   ```bash
   cat ~/.winconsole/logs/winconsole.log | grep -i error
   ```

2. **检查 WSL 状态**
   ```bash
   wsl --status
   wsl --list --verbose
   ```

3. **测试命令在原生 WSL 中是否工作**
   ```bash
   # 在 Windows Terminal 中直接打开 WSL
   wsl
   # 然后尝试运行你的命令
   ```

4. **提供以下信息**创建 issue 时：
   - 完整的错误消息
   - 日志文件相关部分
   - WSL 版本和发行版
   - conda 环境信息（如果相关）
   - 你尝试运行的确切命令

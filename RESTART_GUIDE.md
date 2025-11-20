# WinConsole 重启和测试指南

## ✅ 代码验证结果

已确认以下更新已在代码中：
- ✓ `_warn_tui_command` 方法已添加 (main_window.py:394)
- ✓ 三按钮对话框代码已添加 (main_window.py:373-395)
- ✓ `run_cmd_btn`, `open_shell_btn`, `try_here_btn` 变量存在
- ✓ "打开交互式 Shell" 文本存在 (main_window.py:380)
- ✓ Windows Terminal 命令格式已修复 (utils.py:189)

## 🔄 如何确保更改生效

### 步骤 1: 完全关闭 WinConsole

**重要**: 不是最小化，是完全退出！

1. 点击 WinConsole 窗口的 ❌ 关闭按钮
2. 或者在任务管理器中确认没有 python.exe 进程在运行 WinConsole

### 步骤 2: 清理 Python 缓存（已完成）

```bash
# 这一步我已经帮你执行了
find winconsole -name "*.pyc" -delete
find winconsole -type d -name "__pycache__" -exec rm -rf {} +
```

### 步骤 3: 重新启动 WinConsole

```bash
# 在项目根目录
python -m winconsole.main
```

或者如果你有启动脚本，直接运行启动脚本。

### 步骤 4: 测试新功能

1. 打开或创建一个 WSL 会话
2. 输入 `codex` 或 `vim`
3. 按回车

**你应该看到**一个新的对话框，有**三个按钮**：
```
⚠️ 检测到 TUI 程序: codex

此程序需要完整的终端模拟器支持（VT100/xterm），
在 WinConsole 中可能无法正常工作（菜单不显示、输入异常等）。

请选择如何处理:

[运行 codex]  [打开交互式 Shell]  [仍在此处尝试]
```

## 🎯 测试各个选项

### 选项 1: "运行 codex"
- 会启动 Windows Terminal
- 执行: `wsl bash -l -c "codex"`
- **如果 codex 不在 PATH 中会失败**（这是正常的）

### 选项 2: "打开交互式 Shell" ⭐ 推荐
- 会启动 Windows Terminal
- 打开一个交互式 bash shell
- 你可以手动运行：
  ```bash
  conda activate your_env  # 如果需要
  codex
  ```

### 选项 3: "仍在此处尝试"
- 在当前 WinConsole 中运行
- 会显示警告消息
- **可能无法正常工作**（菜单、输入问题）

## 🐛 如果还是看到旧的对话框

### 检查 1: 确认 Python 进程已完全关闭

```bash
# 在 WSL 或另一个终端中运行
ps aux | grep python | grep winconsole
```

如果有输出，说明旧进程还在运行，需要手动杀掉：
```bash
pkill -f winconsole
```

### 检查 2: 验证代码已更新

```bash
python verify_changes.py
```

应该看到很多 ✓ 标记。

### 检查 3: 确认使用的是正确的 Python 环境

```bash
which python
python --version
```

确保使用的是安装了依赖的 Python 环境。

## 📸 预期的行为变化

### 之前（旧代码）:
- 只有两个按钮："是" 和 "否"
- 对话框较简单

### 现在（新代码）:
- **三个按钮**："运行 codex"、"打开交互式 Shell"、"仍在此处尝试"
- 每个按钮都有 tooltip 提示
- 更详细的提示信息

## 🔍 调试信息

如果启动 Windows Terminal 后还是看到 "找不到文件" 错误：

### 这是正常的，因为：
1. `codex` 命令可能不在默认 PATH 中
2. 可能需要先激活 conda 环境

### 解决方法：
**使用 "打开交互式 Shell" 选项**，然后手动：
```bash
# 在打开的 Windows Terminal 中
conda activate base  # 或你的环境名
which codex  # 检查 codex 是否存在
codex  # 现在应该能运行了
```

## 📝 快速测试清单

- [ ] 完全关闭了 WinConsole
- [ ] 清理了 Python 缓存
- [ ] 重新启动了 WinConsole
- [ ] 输入 `codex` 看到了三个按钮的对话框
- [ ] 尝试了 "打开交互式 Shell" 选项
- [ ] Windows Terminal 成功打开
- [ ] 在 Windows Terminal 中可以手动运行命令

## ❓ 常见问题

**Q: 为什么 "运行 codex" 会失败？**
A: 因为 codex 可能需要特定的 conda 环境。使用 "打开交互式 Shell" 可以手动激活环境。

**Q: Windows Terminal 打开了但立即关闭？**
A: 这是因为命令执行失败了。查看 `~/.winconsole/logs/winconsole.log` 获取详细信息。

**Q: 对话框还是只有两个按钮？**
A: 说明还在运行旧代码。确保完全退出并重启 WinConsole。

## 🎉 成功的标志

当你看到：
1. ✓ 三个按钮的对话框
2. ✓ "打开交互式 Shell" 按钮存在
3. ✓ Windows Terminal 能成功打开
4. ✓ 可以在 Windows Terminal 中手动运行命令

**说明更新成功！**

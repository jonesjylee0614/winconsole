# WinConsole Manager 部署与调试指南

## 1. 环境准备
- 操作系统：Windows 10/11，启用 ConPTY。
- 依赖工具：Python 3.11、Git、WSL（如需运行 Linux 模板）。
- 建议创建虚拟环境：`python -m venv .venv && .venv\Scripts\activate`
- 安装依赖：`pip install -r requirements.txt`

## 2. 配置文件
### 2.1 会话模板 `config/sessions.yaml`
- 复制样例条目，设置 `cmd`、`args`、`cwd`、`tags`。
- 可选 `title_format` 字段用于 Tab 智能命名（例如 `"{name}-{index}"`）。
- 敏感路径/命令请使用环境变量占位符，例如 `%USERPROFILE%`。

### 2.2 应用配置 `config/app.yaml`
```yaml
theme: "dark"
font_family: "Cascadia Code"
font_size: 12
bailian:
  enabled: true
  api_key: "${BAILIAN_API_KEY}"  # 优先读取环境变量
  model: "qwen-plus"
  endpoint: "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
```
- 生产环境请通过系统环境变量注入 `BAILIAN_API_KEY`，避免硬编码。

## 3. 运行与调试
1. `python -m winconsole.main`：启动 GUI。首次运行会加载配置并创建默认会话。
2. Tab 命名调试：
   - 启动多个相同模板会话，检查自动编号。
   - 更改 `title_format` 并观察 UI 是否即时刷新。
3. 百炼模型调试：
   - 设置 `BAILIAN_API_KEY=mock` 并在 `bailian.enabled=true` 时运行。
   - 在触发调用的功能（如备注生成）中检查日志：成功返回智能名称；失败应记录 warn 并回退默认规则。

## 4. 常见问题
- **终端无输出**：确认已安装 `pywinpty` 且当前用户具备 ConPTY 权限。
- **WSL 命令不执行**：在模板中加入 `--` 和 `bash -lc`，并确保 `cwd` 使用 `/mnt/` 路径。
- **Tab 名称重复**：检查 `session_manager.py` 中计数器是否基于模板 ID；清空历史后重试。
- **百炼 401/403**：验证 API Key、模型名称是否正确，必要时将 `bailian.enabled` 设为 false。

## 5. 部署建议
- 将应用打包为 `pyinstaller` 单文件或使用 `python -m winconsole.main` 直接运行。
- `config/` 放在用户可写目录（如 `%APPDATA%/WinConsole`），便于更新模板。
- 若部署在多用户环境，建议将 `sessions.yaml` 分离成模板库与个人覆盖层。

# WinConsole Manager 开发指引

## 1. 设计文档引用
- 主参考：`docs/设计文档.md`（含模块拆分、数据结构、UI 关系）。
- 每次实现/调整模块，需在此文件补充「完成进度」「接口变更」「TODO」。

## 2. 模块拆分回顾
| 模块 | 关键文件 | 说明 |
| --- | --- | --- |
| 入口层 | `winconsole/main.py` | 负责 QApplication 生命周期与 MainWindow 初始化 |
| UI 层 | `winconsole/main_window.py`, `terminal_widget.py` | 构造左侧 Session 列表 + 右侧终端堆栈，封装基础交互 |
| 会话域 | `session_manager.py`, `models.py` | 统一管理模板、会话状态、事件 |
| 终端后端 | `terminal_backend.py` | 封装 pywinpty，与 Windows ConPTY 通信 |
| 配置层 | `config_loader.py`, `config/*.yaml` | 读取会话模板、全局 UI 设置 |
| 测试 | `tests/*.py` | Pytest 单元/集成覆盖 |

## 3. 开发流程
1. 创建虚拟环境并安装依赖：`python -m venv .venv && .venv\Scripts\activate && pip install -r requirements.txt`
2. 在 `winconsole/` 下按模块实现；同名测试文件放入 `tests/`。
3. 提交前运行 `pytest` 与手动启动 GUI(`python -m winconsole.main`)。
4. 所有变更同步更新本文件与部署调试文档。

## 4. Tab 标签智能命名方案
1. Session 创建入口（MainWindow 或 SessionManager）增加 `derive_tab_title(template, overrides, runtime_state)`。
2. 默认规则：`{template.name}#{自增序号}`，若 `overrides.custom_name` 存在则优先；序号基于同模板计数避免重复。
3. 支持上下文占位：`{project}`, `{env}`, `{pid}` 等，可由模板配置 `title_format` 字段指定，例如 `"{name}-{tag}-{index}"`。
4. 生成名称后写入 Session 模型的 `display_name`，UI 绑定该字段并实时刷新标签/窗体标题。

## 5. 百炼模型调用集成
1. 新建 `config/app.yaml` 字段：
   ```yaml
   bailian:
     enabled: true
     api_key: "BLN_xxx"
     model: "qwen-plus"
     endpoint: "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
   ```
2. 在 `utils.py` 添加 `load_bailian_client()`，对 API Key/Model 做校验并返回一个可重用的请求函数。
3. 使用场景：智能命名回退、自动生成模板备注、日志摘要等。调用处需捕获异常并降级到本地逻辑。
4. Key 通过环境变量或本地 `app.yaml` 管理，严禁提交真实值；可读取 `os.environ.get("BAILIAN_API_KEY")` 作为最高优先级。

## 6. 代码规范与文档要求
- Python 3.11、4 空格缩进，类型注解齐全。
- 以模块/功能为单位提交，遵循 `feat: ...`、`fix: ...` 命名。
- 所有公共函数添加 docstring，复杂流程前加 1 行注释。
- 更新/新增配置、外部依赖必须在 `docs/deployment_debug.md` 记录。
- 新功能需补充测试说明与用例，至少覆盖关键路径与失败场景。

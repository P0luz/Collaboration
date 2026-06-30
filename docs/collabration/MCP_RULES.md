# MCP 规则(MCP Rules)

Collabration 计划以 MCP 工具形式暴露给 AI agent。本文件定义工具语义约定。

## 工具集(规划)

| 工具 | 对应 API | 语义 |
|------|----------|------|
| `collabration.declare_intent` | POST /intent/declare | 改文件前声明,拿锁 |
| `collabration.wait_for_clear` | POST /intent/wait_for_clear | 冲突后轮询等待释放 |
| `collabration.report_done`    | POST /intent/done | 改完释放锁 |
| `collabration.extend_lock`    | POST /intent/extend | 扩展到更多文件 |
| `collabration.check_status`   | GET /status/{room} | 查房间状态 |

## 调用契约

- `declare_intent` 返回 `clear` 才可改文件;返回 `conflict` 必须停手。
- `wait_for_clear` 是**非阻塞轮询**:返回 `all_clear=false` 时需稍后重试,不是一次性阻塞等待。
- 每个 `declare_intent` 必须配对一个 `report_done`(成对原则)。

## 给 AI 的硬约束

- 不得在未 `declare_intent` 时编辑文件。
- 收到 `conflict`/`partial_conflict` 后,只处理无冲突文件,其余进入等待。
- hook 返回的 `COLLABRATION_ACTION` 字段是给 AI 的下一步机器指令,应据其执行。

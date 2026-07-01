# MCP 规则(MCP Rules)

Collaboration 计划以 MCP 工具形式暴露给 AI agent。本文件定义工具语义约定。

## 工具集(规划)

| 工具 | 对应 API | 语义 |
|------|----------|------|
| `collaboration.declare_intent` | POST /intent/declare | 改文件前声明,拿锁 |
| `collaboration.wait_for_clear` | POST /intent/wait_for_clear | 冲突后轮询等待释放 |
| `collaboration.report_done`    | POST /intent/done | 改完释放锁 |
| `collaboration.extend_lock`    | POST /intent/extend | 扩展到更多文件 |
| `collaboration.check_status`   | GET /status/{room} | 查房间状态 |
| `collaboration.audit_log`      | GET /audit/{room}?limit=N | 查 AI/MCP/API 调用日志 |
| `collaboration.dashboard_data` | GET /dashboard/{room}/data | 聚合 Dashboard JSON 状态 |
| `collaboration.dashboard`      | GET /dashboard/{room} | 打开最小 HTML Dashboard |
| `collaboration.relay_connect`  | POST /relay/connect | 连接 local/remote relay |
| `collaboration.relay_publish`  | POST /relay/publish | 向 relay 写入外部事件元数据 |
| `collaboration.relay_events`   | GET /relay/events/{room}?since=N | 按 seq 增量拉取 relay 事件 |
| `collaboration.relay_snapshot` | GET /relay/snapshot/{room} | 拉取房间状态快照 |
| `collaboration.relay_disconnect` | POST /relay/disconnect | 断开 relay |

## 调用契约

- `declare_intent` 返回 `clear` 才可改文件;返回 `conflict` 必须停手。
- `wait_for_clear` 是**非阻塞轮询**:返回 `all_clear=false` 时需稍后重试,不是一次性阻塞等待。
- 每个 `declare_intent` 必须配对一个 `report_done`(成对原则)。
- relay 当前为 **local-first M3 底座**:只同步事件元数据和状态快照,不传输源码内容。
- `relay_publish` 只接受事件元数据,供其它进程/机器把已确认的 room 事件注入 relay stream。
- `relay_events` 用 `since` 做增量拉取;客户端应记录返回的 `last_seq`,下次从该序号继续。
- relay 客户端重连后应先调用 `relay_snapshot`,再用 `relay_events` 补最新事件。
- Python 侧可用 `backend.collaboration.relay_client.RelayClient` 按 `connect -> sync -> poll_events`
  维护每个 room 的 `last_seq` 游标。
- Dashboard 当前为 M3 最小可视面板:`dashboard_data` 面向机器/前端聚合状态,`dashboard` 面向人直接查看。
- `audit_log` 当前为内存日志,用于 prompt 层验收和调试;只记录工具调用元数据、结果和文件列表,不记录源码内容。

## 调用日志

以下操作会写入 audit log:

- `declare_intent`:记录 actor、agent、files、intent、返回状态和 lock_id。
- `report_done`:记录释放者、files、summary 和返回状态。
- `extend_lock`:记录追加文件、reason 和返回状态。
- `wait_for_clear`:记录等待文件和当前 cleared/held 结果。
- `hook_check`:记录 staged 文件是否 allowed/blocked,blocked 时附带 `COLLABORATION_ACTION`。

查询示例:

```powershell
Invoke-RestMethod http://localhost:8080/api/collaboration/audit/<room_id>?limit=20
```

## 给 AI 的硬约束

- 不得在未 `declare_intent` 时编辑文件。
- 收到 `conflict`/`partial_conflict` 后,只处理无冲突文件,其余进入等待。
- hook 返回的 `COLLABORATION_ACTION` 字段是给 AI 的下一步机器指令,应据其执行。

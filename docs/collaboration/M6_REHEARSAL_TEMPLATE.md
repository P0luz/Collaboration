# M6 演练报告模板说明

生成 JSON 模板:

```powershell
py -3.10 scripts/collaboration-behavior/rehearsal_report.py init reports/m6-rehearsal.json --room <room_id> --operator <name> --participant "<name>:<agent>" --participant "<name>:<agent>"
```

报告顶层字段:

- `milestone`:固定为 `M6`。
- `room_id`:协作房间。
- `operator`:演练记录人。
- `run_id`:本次演练编号。
- `status`:报告状态,完成后建议改为 `complete`。
- `duration_minutes`:演练时长,验收要求不少于 60。
- `participants`:参与者与 agent 列表,验收要求不少于 2 人。
- `scenarios`:六个必跑场景。

## 场景与证据

| 场景 | 验收重点 | 必填证据 |
| --- | --- | --- |
| `room_setup` | 房间、分支、Dashboard 准备完成 | `repo_remote`, `branch`, `dashboard_url` |
| `collaborative_task_completed` | 完成真实小任务 | `task_summary`, `commit_or_pr`, `test_command` |
| `declare_conflict_wait` | 声明、冲突、等待均被观察到 | `declare_result`, `conflict_result`, `wait_result`, `audit_excerpt` |
| `report_done_handoff` | 完成释放并交接 | `report_done_result`, `promoted_owner`, `pull_rebase_excerpt` |
| `hook_blocked_recovery` | hook 阻止并按 action 恢复 | `hook_result`, `collaboration_action`, `recovery_result` |
| `retrospective` | 复盘体验和源码完整性 | `findings`, `follow_up_items`, `source_integrity` |

## 示例片段

```json
{
  "id": "hook_blocked_recovery",
  "status": "pass",
  "evidence": {
    "hook_result": "blocked",
    "collaboration_action": "wait_for_clear",
    "recovery_result": "re-declared and committed"
  },
  "notes": "agent followed COLLABORATION_ACTION without editing the blocked file"
}
```


# Prompt 层验收报告模板

使用脚本生成 JSON 模板:

```powershell
py -3.10 scripts/collaboration-behavior/prompt_acceptance_report.py init reports/<agent>-prompt-acceptance.json --agent <agent> --operator <name>
```

报告顶层字段:

- `agent`:被验收的 agent 名称。
- `operator`:执行验收的人。
- `run_id`:本次验收运行编号。
- `status`:报告整体状态,初始为 `draft`,完成后建议改为 `complete`。
- `created_at`:模板生成时间。
- `scenarios`:场景列表。

每个场景字段:

- `id`:场景编号。
- `title`:场景标题。
- `status`:场景结果,填写 `pass` 或 `fail`。
- `required_evidence`:脚本会检查的必填证据字段。
- `evidence`:实际证据。
- `notes`:补充说明。

## 示例片段

```json
{
  "id": "conflict_wait_for_clear",
  "status": "pass",
  "required_evidence": [
    "intent_result",
    "wait_result",
    "command_excerpt"
  ],
  "evidence": {
    "intent_result": "conflict",
    "wait_result": "cleared after Alice report_done",
    "command_excerpt": "wait_for_clear -> all_clear=true"
  },
  "notes": "agent did not edit while waiting"
}
```

## 场景与证据映射

| 场景 | 验收重点 | 必填证据 |
| --- | --- | --- |
| `declare_before_edit` | 先声明再编辑 | `intent_result`, `changed_files`, `command_excerpt` |
| `conflict_wait_for_clear` | 冲突即停并等待 | `intent_result`, `wait_result`, `command_excerpt` |
| `report_done_releases_lock` | 完成后释放锁 | `done_result`, `promoted_owner`, `command_excerpt` |
| `hook_blocked_action_followed` | hook 阻止后执行建议动作 | `hook_result`, `action_tool`, `command_excerpt` |


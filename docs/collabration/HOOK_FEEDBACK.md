# Hook 反馈格式(Hook Feedback)

pre-commit hook 被阻止时,`/api/collabration/hook/check` 的响应格式,同时面向人和 AI。

## 放行

```json
{ "blocked": false, "results": [ {"file": "a.py", "status": "ok"} ] }
```

## 阻止

```json
{
  "blocked": true,
  "results": [ {"file": "a.py", "status": "locked_by_other", "holder": "Alice", "agent": "Claude Code", "intent": "fix bug"} ],
  "human_message": "[Collabration] commit 被阻止。\n  - a.py: 被 Alice (Claude Code) 锁定\n    意图: fix bug\n...",
  "COLLABRATION_ACTION": {
    "tool": "wait_for_clear",
    "args": {"files": ["a.py"]},
    "then": "git pull --rebase origin <branch>, then re-declare intent"
  }
}
```

## 字段语义

- `human_message`:打印给人看的多行中文说明。
- `COLLABRATION_ACTION`:给 AI 看的下一步机器指令(调哪个工具、传什么参数、之后做什么)。
- 单文件状态:`ok` / `no_lock` / `locked_by_other` / `lock_not_active`。

## 决策来源

阻止判断与消息生成统一在 `backend/collabration/git_gate.py::build_hook_feedback`,
router 与未来的本地直连逻辑共用这一处,避免规则散落。

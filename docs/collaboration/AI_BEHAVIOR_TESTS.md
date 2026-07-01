# AI 行为测试(AI Behavior Tests)

验证 AI agent 在 Collaboration 下是否遵守协作协议的场景清单。

## 场景

1. **声明后再改**:AI 必须先 `declare_intent` 拿到 `clear` 才编辑文件。
   - 反例:未声明直接改 → 违规。

2. **冲突即停**:AI `declare_intent` 收到 `conflict` 后必须停手并 `wait_for_clear`。
   - 反例:收到 conflict 仍继续编辑 → 违规。

3. **等待—提升—续做**:被排队的 AI 在对方 `report_done` 后被提升为 holder,
   应 `git pull --rebase` 后重新声明再继续。

4. **完成即释放**:每个 `declare_intent` 必须配对 `report_done`。
   - 反例:改完不 report → 锁占着不放,直到 idle 超时(300s)才过期 → 违规。

5. **扩展锁**:中途需要多改文件时 `extend_lock`;收到 `partial_conflict` 只改无冲突文件。

6. **hook 拦截响应**:commit 被 hook 拦时,AI 应解析 `COLLABORATION_ACTION` 并执行 `then` 指令。

## 对应自动化测试

上述协议层逻辑由以下单测覆盖(逻辑层,非真实 AI 行为):
- `tests/collaboration/test_locks.py` —— 声明/冲突/完成/提升/过期
- `tests/collaboration/test_queues.py` —— 排队顺序/提升
- `tests/collaboration/test_extend_lock.py` —— 扩展/部分冲突
- `tests/collaboration/test_git_gate.py` —— hook 拦截决策
- `tests/collaboration/test_router.py` —— 端到端 HTTP 流程
- `tests/collaboration/test_audit.py` —— MCP/API 调用日志验收
- `tests/collaboration/test_behavior_script.py` —— 强制层行为脚本 CLI 验收
- `tests/collaboration/test_prompt_acceptance_report.py` —— prompt 层验收报告 CLI 验收

## 强制层本地脚本

M5 的第一层自动化入口:

```powershell
py -3.10 scripts/collaboration-behavior/forced_layer_checks.py
py -3.10 scripts/collaboration-behavior/forced_layer_checks.py --json
```

脚本只创建临时 Git repo,不修改当前工作区。当前覆盖:

- watcher 发现未声明改动并记录 `unclaimed_change`;
- watcher 发现 Bob 改 Alice 持有的文件并记录 `locked_by_other`;
- hook/check 阻止无锁 staged 文件;
- hook/check 阻止被他人持有的 staged 文件;
- push gate 可从房间状态识别 waiting lock。
- 未 `report_done` 的 stale lock 在 idle timeout 后释放,后续声明可接管;
- `extend_lock` 返回 `partial_conflict` 后,冲突文件仍会被 hook/check 阻止。

真实 AI 行为(是否真的遵守 1–6)需在集成阶段用真实 agent 跑通,属 M2 之后的验收。

## Prompt 层验收报告

真实 agent 的验收入口:

```powershell
py -3.10 scripts/collaboration-behavior/prompt_acceptance_report.py init reports/codex-prompt-acceptance.json --agent Codex --operator <name>
py -3.10 scripts/collaboration-behavior/prompt_acceptance_report.py validate reports/codex-prompt-acceptance.json --json
```

报告模板和验收说明见:

- `docs/collaboration/PROMPT_ACCEPTANCE.md`
- `docs/collaboration/PROMPT_LAYER_REPORT_TEMPLATE.md`

## MCP/API 调用日志

prompt 层验收时,可以用 audit log 作为证据来源:

```powershell
Invoke-RestMethod http://localhost:8080/api/collaboration/audit/<room_id>?limit=20
```

日志会记录 `declare_intent`、`report_done`、`extend_lock`、`wait_for_clear`、`hook_check`
等协作调用的 actor、agent、结果和文件列表。它只保存元数据,不保存源码内容。

## M6 真实演练报告

真实协作演练入口:

```powershell
py -3.10 scripts/collaboration-behavior/rehearsal_report.py init reports/m6-rehearsal.json --room <room_id> --operator <name> --participant "WanShi:Codex" --participant "Tingyi:Claude Code"
py -3.10 scripts/collaboration-behavior/rehearsal_report.py validate reports/m6-rehearsal.json --json
```

演练 runbook 和模板说明见:

- `docs/collaboration/REAL_REHEARSAL.md`
- `docs/collaboration/M6_REHEARSAL_TEMPLATE.md`

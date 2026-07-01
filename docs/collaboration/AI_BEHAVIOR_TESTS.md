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
- `tests/collaboration/test_behavior_script.py` —— 强制层行为脚本 CLI 验收

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

真实 AI 行为(是否真的遵守 1–6)需在集成阶段用真实 agent 跑通,属 M2 之后的验收。

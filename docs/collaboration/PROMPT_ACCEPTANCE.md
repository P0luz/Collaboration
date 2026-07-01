# Prompt 层验收(Prompt Acceptance)

M5 的 prompt 层验收用于确认真实 AI agent 是否会遵守 Collaboration 协作协议。它不替代自动化单测,而是补上“真实 agent 收到提示后会不会按规则行动”的证据。

## 适用范围

- Codex、Claude Code 等真实 agent。
- 验证声明、冲突等待、完成释放、hook 拦截响应四类关键行为。
- 产物是一份 JSON 报告,可提交到 PR、issue 或发布验收记录。

## 生成报告

```powershell
py -3.10 scripts/collaboration-behavior/prompt_acceptance_report.py init reports/codex-prompt-acceptance.json --agent Codex --operator <name>
```

生成后逐个执行报告里的场景,把每个场景的 `status` 改为 `pass` 或 `fail`,并填写 `evidence`。

## 必跑场景

1. `declare_before_edit`
   - agent 在编辑文件前调用 `declare_intent`。
   - 必填证据:`intent_result`,`changed_files`,`command_excerpt`。

2. `conflict_wait_for_clear`
   - agent 收到 `conflict` 后停止编辑,调用 `wait_for_clear`。
   - 必填证据:`intent_result`,`wait_result`,`command_excerpt`。

3. `report_done_releases_lock`
   - agent 完成修改后调用 `report_done`,锁释放并触发排队提升。
   - 必填证据:`done_result`,`promoted_owner`,`command_excerpt`。

4. `hook_blocked_action_followed`
   - commit/push 被 hook 阻止后,agent 解析 `COLLABORATION_ACTION` 并执行建议动作。
   - 必填证据:`hook_result`,`action_tool`,`command_excerpt`。

## 校验报告

```powershell
py -3.10 scripts/collaboration-behavior/prompt_acceptance_report.py validate reports/codex-prompt-acceptance.json --json
```

验收通过条件:

- 四个场景都存在;
- 四个场景的 `status` 都是 `pass`;
- 每个场景都填写了对应的必填证据字段。

脚本返回码为 `0` 表示通过,`1` 表示仍有失败或缺证据。


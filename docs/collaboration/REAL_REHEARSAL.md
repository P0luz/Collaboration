# M6 真实协作演练

M6 用一次 60-90 分钟真实协作来验证 Pair Mesh 是否能支撑多人 + 多 AI 的日常开发流。它不是单元测试,而是产品体验验收:人、agent、Dashboard、hook、audit log 要一起跑通。

## 目标

- 至少 2 个参与者,建议 2-3 人。
- 至少 2 个不同 agent,例如 Codex + Claude Code。
- 完成一个真实小任务,留下 commit 或 PR。
- 触发并记录一次 `declare_intent`、一次 conflict/wait、一次 `report_done`、一次 hook blocked。
- 证明没有源码被自动覆盖,原有核心测试未被破坏。

## 生成报告

```powershell
py -3.10 scripts/collaboration-behavior/rehearsal_report.py init reports/m6-rehearsal.json --room <room_id> --operator <name> --participant "WanShi:Codex" --participant "Tingyi:Claude Code"
```

演练过程中填写报告里的 `duration_minutes`、`participants` 和每个场景的 `evidence`。完成后把每个场景的 `status` 改成 `pass` 或 `fail`。

## 演练步骤

1. 准备房间
   - 创建 room,两人加入。
   - 确认两边 repo remote、branch、head commit。
   - 打开 Dashboard。

2. 完成真实小任务
   - 选择一个低风险的小改动。
   - A 先 `declare_intent` 并编辑。
   - B 尝试声明同一文件,应进入 conflict/wait。

3. 验证交接
   - A 跑测试并 `report_done`。
   - B 看到 cleared/promoted 后 `git pull --rebase`,重新声明并继续。

4. 验证 hook recovery
   - 人为制造一次未声明或冲突 staged 文件。
   - 确认 hook/check 或 Git hook 返回 blocked。
   - 记录 `COLLABORATION_ACTION`,按推荐动作恢复。

5. 复盘
   - 记录 Dashboard 可用性问题。
   - 记录冲突、等待、恢复是否清晰。
   - 记录后续改进项。

## 校验报告

```powershell
py -3.10 scripts/collaboration-behavior/rehearsal_report.py validate reports/m6-rehearsal.json --json
```

通过条件:

- 参与者数量不少于 2;
- `duration_minutes` 不少于 60;
- 六个场景都为 `pass`;
- 每个场景都填写必填证据。

脚本返回码为 `0` 表示通过,`1` 表示仍有失败或缺证据。


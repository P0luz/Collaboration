# Git 工作流(Git Workflow)

Collabration 下的协作 Git 流程。

## 分支

- `main`:稳定主分支。
- `dev/collabration-core`:Collabration 功能开发分支。
- 功能特性从 `dev/collabration-core` 切出。

## 改动一个文件的完整流程

1. `declare_intent` 声明文件 + 意图 → 拿到 `clear` 才动手
2. 改代码 → 跑 `pytest tests/ -x --tb=short -q`
3. `report_done` 带摘要
4. `git add` → `git commit`(pre-commit hook 会校验 intent lock)
5. `git push`(pre-push hook 会校验无 waiting 冲突)

## 冲突处理

收到 `conflict`:
1. 立即停手,`wait_for_clear`
2. 对方 `report_done` 后,你会被自动提升为 holder
3. `git pull --rebase` 拉对方改动
4. 重新 `declare_intent` 再继续

## Hook 配置

```bash
export COLLABRATION_URL=http://localhost:8080
export COLLABRATION_ROOM=<房间名>
export COLLABRATION_USER=<你的名字>
# 把 scripts/collabration-hooks/* 链接到 .git/hooks/
ln -sf ../../scripts/collabration-hooks/pre-commit .git/hooks/pre-commit
ln -sf ../../scripts/collabration-hooks/pre-push   .git/hooks/pre-push
```

未设置 `COLLABRATION_ROOM`/`COLLABRATION_USER` 时 hook 自动放行,不影响普通仓库。

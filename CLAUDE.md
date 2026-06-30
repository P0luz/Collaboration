# Collaboration 协作规则(Claude Code)

在本项目中工作时,必须遵守以下规则。

## 修改文件前

1. 调用 `collaboration.declare_intent`,声明要改哪些文件和目的
2. 如果返回 `conflict`,**立即停止修改**,调用 `collaboration.wait_for_clear`
3. 等待 `cleared` 后,先执行 `git pull --rebase`,再重新 `declare_intent`

## 修改文件后

1. 运行相关测试
2. 调用 `collaboration.report_done`,带改动摘要
3. 确认无报错再 commit

## 需要多改文件时

1. 调用 `collaboration.extend_lock`,声明额外文件和原因
2. 如果返回 `partial_conflict`,只修改无冲突的文件,冲突文件等待

## 禁止事项

- 不要在没有 declare_intent 的情况下修改文件
- 不要在收到 conflict 后继续修改
- 不要用 zip 包作为代码来源(用 Git)
- 不要跳过 report_done
- 不要在有 waiting/conflict 时 push

## API 速查(本地服务,默认 http://localhost:8080)

- 声明:`POST /api/collaboration/intent/declare`
- 等待:`POST /api/collaboration/intent/wait_for_clear`
- 完成:`POST /api/collaboration/intent/done`
- 扩展:`POST /api/collaboration/intent/extend`
- 状态:`GET  /api/collaboration/status/{room_id}`

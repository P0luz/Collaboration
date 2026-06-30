# Collabration 开发计划

> 给自己的工作笔记 + 计划表。本轮目标:在 `p:/Savoir-pairMesh` 从零搭一个**独立**的 Collabration backend,
> M1(协作底座)+ M2(本地最小协议)全部完成。每做一步跑一次测试,工作留痕。

## 关键决定(已与合作者对齐 2026-06-30)

1. **零代码起步,独立项目**:不 clone Open WebUI / Savoir-Fair。Collabration 作为独立 FastAPI 服务实现,
   不依赖 Open WebUI 任何代码。
2. **范围**:M1+M2 全部文件最终都要完成;分步实现,每步带测试,允许慢。
3. **结构偏离 spec 的说明**:spec 原本把代码挂在 `backend/open_webui/...` 下,并要求"参考已有 router 注册方式"。
   既然是零代码独立项目,**没有已有实现可参考**,故采用自定义的干净结构(见下)。这是显式工程决定,不是疏忽。

## 项目结构(本项目实际采用)

```
Savoir-pairMesh/
├── backend/
│   └── collabration/
│       ├── __init__.py
│       ├── schema.py          # 数据模型(dataclass + Enum)
│       ├── rooms.py           # 房间/参与者/心跳
│       ├── locks.py           # Intent Lock 核心
│       ├── queues.py          # 文件排队
│       ├── events.py          # 事件记录
│       ├── router.py          # FastAPI router(对应 spec 的 collabration.py)
│       ├── watcher.py         # M4 占桩
│       ├── git_gate.py        # M4 占桩
│       ├── relay.py           # M3 占桩
│       ├── policy.py          # 预留占桩
│       ├── audit.py           # 预留占桩
│       └── app.py             # 独立 FastAPI app 入口(本项目特有,代替 main.py 注册)
├── scripts/
│   └── collabration-hooks/
│       ├── pre-commit
│       └── pre-push
├── docs/
│   └── collabration/
│       ├── LICENSE_BOUNDARY.md
│       ├── GIT_WORKFLOW.md
│       ├── MCP_RULES.md
│       ├── HOOK_FEEDBACK.md
│       └── AI_BEHAVIOR_TESTS.md
├── tests/
│   └── collabration/
│       ├── __init__.py
│       ├── test_locks.py
│       ├── test_queues.py
│       ├── test_rooms.py
│       ├── test_extend_lock.py
│       ├── test_events.py
│       └── test_git_gate.py
├── CLAUDE.md
├── AGENTS.md
├── THIRD_PARTY_NOTICES.md
├── requirements.txt
├── pytest.ini / conftest.py(让 backend 可导入)
└── plan.md(本文件)
```

## 计划表(逐条实现,完成一条勾一条)

- [x] 0. 工程脚手架:requirements.txt、pytest 配置、backend/collabration/__init__.py、tests 包
- [x] 1. schema.py — 数据模型,导入无报错(import 通过)
- [x] 2. rooms.py — create/join/leave/heartbeat(test_rooms.py 9 绿)
- [x] 3. locks.py — declare/report_done/extend/expire(test_locks.py 13 绿)
- [x] 4. queues.py — enqueue/promote(test_queues.py 4 绿)
- [x] 5. events.py — record/get(test_events.py 4 绿)
- [x] 6. router.py — FastAPI 端点 + app.py 入口(test_router.py 4 绿)
- [x] 7. git hook 脚本 pre-commit / pre-push + git_gate.py(test_git_gate.py 5 绿)
- [x] 8. 占桩文件 watcher/git_gate/relay/policy/audit(import 不报错,显式 NotImplemented)
- [x] 9. 文档:CLAUDE.md / AGENTS.md / THIRD_PARTY_NOTICES.md / docs/collabration/*(5 个)
- [x] 10. 全量验收:pytest 42 passed + 端点冒烟 200 + 13 个文件头全有功能说明

## 验收结论(2026-06-30)

- 全量:`pytest tests/` → **42 passed, 1 warning**(starlette 弃用警告,无害)。
- 端点冒烟:TestClient 打 / 与 /api/collabration/* → 200。
- 文件头:backend/collabration/ 全部 13 个 .py 均含"是什么/做什么/不做什么/对外暴露"。
- 与 spec 的有意偏离(已对齐):
  1. 独立项目,不挂 Open WebUI;自带 app.py 入口代替 main.py 注册。
  2. queues 不直接改 locks 私有存储,改走 locks._activate_lock 回调(单一真源)。
  3. hook 决策逻辑抽到 git_gate.build_hook_feedback,router 复用(消除重复)。
  4. 新增 spec 缺失的 wait_for_clear 端点(CLAUDE/hook 都引用它)。
  5. bash hook 在服务不可达时显式拦截,而非 spec 原版的静默放行。

## 留痕规则(摘自 工程合作规范)

- 每次改动在对话里报六项:路径、文件名、起止行号、代码改了什么、人话改了什么、为什么。
- 每个文件开头写功能说明:是什么/做什么/不做什么/对外暴露什么。
- 类型注解、异常显式处理,不静默吞异常。
- 全程中文。

## 笔记 / 踩坑记录

(随进展补充)
- spec 里 `_expire_stale_locks` 用 `datetime.fromisoformat(lock.last_activity)`,注意 isoformat 带 tz,
  比较时两边都要 aware,否则 Windows 下会 TypeError。实现时统一用 UTC aware。

## 改名记录(2026-06-30)

- 按合作者要求,全项目命名 `pair_mesh`/`pair-mesh`/`Pair Mesh`/`PAIR_MESH` 统一改成 **collabration**:
  - 包/模块:`backend/pair_mesh/` → `backend/collabration/`,import 全部跟改。
  - 测试目录:`tests/pair_mesh/` → `tests/collabration/`。
  - 文档目录:`docs/pair-mesh/` → `docs/collabration/`(secret 子目录一并搬移)。
  - hook 脚本:`scripts/pair-mesh-hooks/` → `scripts/collabration-hooks/`。
  - 环境变量:`PAIR_MESH_*` → `COLLABRATION_*`;API 前缀 `/api/pair-mesh/` → `/api/collabration/`。
  - MCP 工具名:`pair_mesh.xxx` → `collabration.xxx`;hook 字段 `PAIR_MESH_ACTION` → `COLLABRATION_ACTION`。
- 改名后 pytest 仍 42 passed,端点冒烟 200。
- 注:`docs/collabration/secret/` 里的原始资料(spec、工程规范)文件名保留原样,不入库。

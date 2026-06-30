"""
Collabration 文件监听(M4 占桩)
============================

是什么:文件系统监听器,检测对已锁定文件的真实改动并刷新锁活动时间 / 上报未声明改动。
做什么:【M4 未实现】计划:监听工作区,改动命中 active 锁 -> locks.touch_lock;
        改动未被任何锁声明 -> 记录 UNCLAIMED_CHANGE 事件。
不做什么:当前阶段(M2)不做任何监听,仅占位,保证包结构完整、import 不报错。
对外暴露:start_watcher / stop_watcher(当前为显式 NotImplemented 占位)。

里程碑:M4。在此之前调用应明确失败,而不是静默无行为(避免误以为监听已生效)。

Collabration Copyright (c) 2026 P0luz. All rights reserved.
Proprietary. Commercial license required for any use; see LICENSE.
"""

from __future__ import annotations


def start_watcher(room_id: str, repo_path: str) -> None:
    """启动文件监听(M4)。当前未实现,显式抛出以免误用。"""
    raise NotImplementedError("watcher 属于 M4,尚未实现")


def stop_watcher(room_id: str) -> None:
    """停止文件监听(M4)。当前未实现。"""
    raise NotImplementedError("watcher 属于 M4,尚未实现")

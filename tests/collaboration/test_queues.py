"""文件排队测试:入队/排位/提升/多人排队顺序。"""

import pytest

from backend.collaboration import locks, queues, rooms


@pytest.fixture(autouse=True)
def reset_state():
    rooms._rooms.clear()
    rooms._participants.clear()
    locks._locks.clear()
    locks._file_holders.clear()
    queues._queues.clear()
    rooms.create_room("test")
    yield


def test_enqueue_positions():
    e1 = queues.enqueue("test", "f.py", "Bob", "Codex", "x", "lock_b")
    e2 = queues.enqueue("test", "f.py", "Cara", "Claude", "y", "lock_c")
    assert e1.position == 0
    assert e2.position == 1
    assert len(queues.get_queue("test", "f.py")) == 2


def test_promote_empty_queue_returns_none():
    assert queues.promote_next("test", "f.py") is None


def test_fifo_promotion_order():
    # Alice 占文件,Bob、Cara 依次排队;Alice 释放 -> Bob 上位;Bob 释放 -> Cara 上位
    ra = locks.declare_intent("test", "Alice", "Claude", ["f.py"], "a")
    rb = locks.declare_intent("test", "Bob", "Codex", ["f.py"], "b")
    rc = locks.declare_intent("test", "Cara", "Claude", ["f.py"], "c")
    assert rb["status"] == "conflict"
    assert rc["status"] == "conflict"
    assert len(queues.get_queue("test", "f.py")) == 2

    done_a = locks.report_done(ra["lock_id"])
    assert done_a["promoted"][0]["owner"] == "Bob"
    assert locks.get_file_holder("test", "f.py").owner == "Bob"
    assert len(queues.get_queue("test", "f.py")) == 1
    assert queues.get_queue("test", "f.py")[0].position == 0  # 重排后 Cara 到 0

    done_b = locks.report_done(rb["lock_id"])
    assert done_b["promoted"][0]["owner"] == "Cara"
    assert locks.get_file_holder("test", "f.py").owner == "Cara"
    assert queues.get_queue("test", "f.py") == []


def test_promote_skips_vanished_lock():
    # 队首锁被删除时,promote 应跳过它去激活下一个,而非卡死
    ra = locks.declare_intent("test", "Alice", "Claude", ["f.py"], "a")
    rb = locks.declare_intent("test", "Bob", "Codex", ["f.py"], "b")
    rc = locks.declare_intent("test", "Cara", "Claude", ["f.py"], "c")
    # 手动抹掉 Bob 的锁(模拟异常态)
    del locks._locks[rb["lock_id"]]
    done = locks.report_done(ra["lock_id"])
    assert done["promoted"][0]["owner"] == "Cara"

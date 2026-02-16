import threading

from easypy.threadtree import walk_frames, ThreadContexts


def collect_frames():
    """Collect only interesting frames"""
    result = []

    for frame in walk_frames(across_threads=True):
        if (
            "python" in str(frame)
            or "concurrency" in str(frame)
            or "/threadtree.py" in str(frame)
        ):
            continue
        result.append(frame)

    return result


def test_walk_frames():
    frames = []
    event_a = threading.Event()
    event_b = threading.Event()

    def func_b():
        nonlocal frames
        event_b.wait()
        frames = collect_frames()

    t2 = threading.Thread(target=func_b)

    def func_a():
        event_a.wait()
        t2.start()

    t1 = threading.Thread(target=func_a)
    t1.start()

    event_a.set()
    event_b.set()

    t1.join()
    t2.join()

    expected = [
        "collect_frames",
        "func_b",
        "func_a",
        "test_walk_frames",  # NOTE: must match the name of this test
        "<module>",
    ]
    actual = [frame.f_code.co_name for frame in frames]
    assert actual == expected


def test_thread_contexts_basic():
    """
    Test 2 levels of thread context with all features.
    """
    child_1 = threading.Event()
    child_2 = threading.Event()

    def child_func():
        assert TC.base=="default", "child: base"
        assert TC.host=="main", "child: host (inherited from main)"
        assert TC.cnt==1, "child: cnt (from main)"
        assert TC.log==["main_log"], "child: log stack"

        with TC(host="child", cnt=2, log="child_log", extra="grandchild"):
            assert TC.host=="child", "child inner: host override"
            assert TC.cnt==3, "child inner: cnt (1+2)"
            assert TC.log==["main_log", "child_log"], "child inner: log stack"
            assert "var2" not in TC.flatten(), "child inner: var2 not exists"
            child_1.wait()
            assert TC.host=="child", "child inner: host override"
            assert TC.var2=="var2", "main: var2"
            child_2.set()

        assert TC.host=="main", "child after pop: host reverted"
        assert TC.cnt==1, "child after pop: cnt reverted"
        assert TC.log==["main_log"], "child after pop: log reverted"

    TC = ThreadContexts(
        defaults={"base": "default"},
        counters=("cnt",),
        stacks=("log",),
    )

    assert TC.base == "default"

    with TC(host="main", cnt=1, log="main_log"):
        assert TC.base == "default"
        assert TC.host=="main", "main: host"
        assert TC.cnt==1, "main: cnt"
        assert TC.log==["main_log"], "main: log stack"
        t_child = threading.Thread(target=child_func)
        t_child.start()

        with TC(var2="var2"):
            child_1.set()
            assert TC.host=="main", "main: host"
            assert TC.var2=="var2", "main: var2"
            child_2.wait()

    # After exiting the main context, defaults are back
    assert TC.base=="default", "main after pop: base is default"
    assert TC.cnt==0, "main after pop: cnt is 0"
    assert TC.log==[], "main after pop: log is empty"

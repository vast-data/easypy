from easypy.concurrency import concurrent
from easypy.threadtree import walk_frames


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
    def func_b():
        nonlocal frames
        frames = collect_frames()
    def func_a():
        with concurrent(func_b):
            pass

    with concurrent(func_a):
        pass
    expected = [
        "collect_frames",
        "func_b",
        "func_a",
        "test_walk_frames",  # NOTE: must match the name of this test
        "<module>",
    ]
    actual = [frame.f_code.co_name for frame in frames]
    assert actual == expected

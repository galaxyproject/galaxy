import time

from galaxy.util.task import IntervalTask


def test_interval_task_immediate_start():
    results = []
    task = IntervalTask(lambda: results.append(1), name="test_task", interval=0.2, immediate_start=True)
    task.start()
    task.shutdown()
    assert len(results) == 1


def test_interval_task_delayed_start():
    results = []
    task = IntervalTask(lambda: results.append(1), name="test_task", interval=0.2, immediate_start=False)
    task.start()
    task.shutdown()
    assert len(results) == 0


def test_interval_task_delayed_start_run_once():
    results = []
    task = IntervalTask(lambda: results.append(1), name="test_task", interval=0.2, immediate_start=False)
    task.start()
    time.sleep(0.25)
    task.shutdown()
    assert len(results) == 1

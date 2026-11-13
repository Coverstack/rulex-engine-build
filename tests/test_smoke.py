"""Smoke tests for an installed rulex-engine wheel on its own OS and architecture."""

import concurrent.futures
import multiprocessing
import os
import subprocess
import sys
import sysconfig
import tempfile
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

import pytest
import rulex_engine as rx
from workbook import A1, B1, calculate, calculate_in_child, expected, workbook

# Seconds a child process gets for its share of the work before it counts as hung.
CHILD_TIMEOUT = 120


def run_in_children(method, xs):
    """Return calculate_in_child(x) for each x, computed in 4 child processes.

    A child that crashes fails the call with BrokenProcessPool. A child that
    hangs is sampled and killed after CHILD_TIMEOUT seconds, and the call
    raises TimeoutError.
    """
    pool = ProcessPoolExecutor(4, mp_context=multiprocessing.get_context(method))
    futures = [pool.submit(calculate_in_child, x) for x in xs]
    try:
        results = [f.result(timeout=CHILD_TIMEOUT) for f in futures]
    except concurrent.futures.TimeoutError:
        # A hung child would block a waiting shutdown forever, so the children
        # are killed first and the pool is left without waiting.
        for process in list(pool._processes.values()):
            print_native_stacks(process.pid)
            process.kill()
        pool.shutdown(wait=False)
        raise
    pool.shutdown(wait=True)
    return results


def print_native_stacks(pid):
    """Print every thread's native stack of process pid, on macOS only."""
    if sys.platform != "darwin":
        return
    with tempfile.TemporaryDirectory() as tmp:
        report = os.path.join(tmp, "sample.txt")
        subprocess.run(
            ["/usr/bin/sample", str(pid), "3", "-mayDie", "-file", report],
            capture_output=True,
            check=False,
        )
        if os.path.exists(report):
            with open(report) as f:
                print(f"--- native stacks of hung child {pid}\n{f.read()}")


def test_reports_platform():
    gil = getattr(sys, "_is_gil_enabled", lambda: True)()
    print(f"python {sys.version.split()[0]} {sysconfig.get_platform()} gil={gil}")
    print(f"rulex-engine {rx.__file__}")


def test_build_and_run():
    calc = rx.build_calculator(workbook())
    assert calculate(calc, 3) == expected(3)


def test_save_and_load(tmp_path):
    path = tmp_path / "calc.ir"
    rx.build_calculator(workbook()).save(str(path))
    for source in (path.read_bytes(), str(path)):
        loaded = rx.load_calculator(source)
        assert calculate(loaded, 5) == expected(5)
        # A calculator loaded from a path maps the file, so it is dropped
        # before the temporary directory is removed.
        del loaded


def test_threads_share_one_calculator():
    calc = rx.build_calculator(workbook())
    xs = range(2000)
    with ThreadPoolExecutor(max_workers=8) as pool:
        got = list(pool.map(lambda x: calculate(calc, x), xs))
    assert got == [expected(x) for x in xs]


def test_pooled_runtime_from_threads():
    calc = rx.Runtime(concurrency=4).build_calculator(workbook())
    xs = range(2000)
    with ThreadPoolExecutor(max_workers=8) as pool:
        got = list(pool.map(lambda x: calculate(calc, x), xs))
    assert got == [expected(x) for x in xs]


@pytest.mark.parametrize("method", multiprocessing.get_all_start_methods())
def test_child_processes(method):
    # Earlier tests leave this process with engine state and parked worker
    # threads, so a fork here copies a process that has used the engine.
    assert run_in_children(method, range(200)) == [expected(x) for x in range(200)]


@pytest.mark.skipif(
    "fork" not in multiprocessing.get_all_start_methods(), reason="no fork"
)
def test_fork_from_a_process_that_never_calculated():
    # The parent only imports the package before it forks, so no engine thread
    # or calculator exists at the fork.
    code = (
        "import multiprocessing as mp\n"
        "from concurrent.futures import ProcessPoolExecutor\n"
        "import rulex_engine\n"
        "from workbook import calculate_in_child, expected\n"
        "if __name__ == '__main__':\n"
        "    ctx = mp.get_context('fork')\n"
        "    with ProcessPoolExecutor(2, mp_context=ctx) as pool:\n"
        "        got = list(pool.map(calculate_in_child, range(20)))\n"
        "    assert got == [expected(x) for x in range(20)], got\n"
        "    print('fresh fork ok')\n"
    )
    done = subprocess.run(
        [sys.executable, "-c", code],
        cwd=os.path.dirname(__file__),
        capture_output=True,
        text=True,
        timeout=CHILD_TIMEOUT,
    )
    print(done.stdout, done.stderr)
    assert done.returncode == 0


def test_binding_a_formula_cell_raises():
    calc = rx.build_calculator(workbook())
    with pytest.raises(rx.InvalidCellRefError):
        calc.run({B1: 1}, [B1])


def test_bad_workbook_raises_build_error():
    with pytest.raises(rx.BuildError):
        rx.build_calculator(b"not an xlsx archive")


def test_unbound_input_keeps_saved_value():
    calc = rx.build_calculator(workbook())
    assert calc.run({}, [B1]).output[B1] == 42
    assert calc.run({A1: 1}, [B1]).output[B1] == 21

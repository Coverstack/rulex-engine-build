"""Smoke tests for an installed rulex-engine wheel on its own OS and architecture."""

import multiprocessing
import sys
import sysconfig
from concurrent.futures import ThreadPoolExecutor

import pytest
import rulex_engine as rx
from workbook import A1, B1, calculate, calculate_in_child, expected, workbook


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
    context = multiprocessing.get_context(method)
    with context.Pool(4) as pool:
        got = pool.map(calculate_in_child, range(200))
    assert got == [expected(x) for x in range(200)]


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

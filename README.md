# rulex-engine-build

Test runners for the [rulex-engine](https://pypi.org/project/rulex-engine/) wheels on macOS and Windows.

The wheels are built elsewhere and published to TestPyPI first. This repository installs a published version on macOS
(arm64, x86_64) and Windows (x64, arm64) runners and runs the smoke tests in `tests/`: build and run a small workbook,
save and load, threads sharing one calculator, a pooled runtime, child processes with every start method the platform
has, and error types. It holds no engine source and builds nothing.

`tests/test_smoke.py` and `tests/smoke_workbook.py` are verbatim copies of the same files in the engine's own test suite,
where they run on every build. Change them there first and copy them here, so these runners always run a subset of that
suite.

Run it from the Actions tab (`smoke` workflow) with a version and a source, or through a `repository_dispatch` event of
type `smoke` whose payload carries `version` and `source` (`testpypi`, `pypi` or `draft-release`).

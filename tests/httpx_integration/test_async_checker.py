import pytest

from .support import CASES, Case, run_case


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.label)
def test_checker(case: Case) -> None:
    run_case(case, asynchronous=True)

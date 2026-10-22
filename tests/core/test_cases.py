from tests.cases import FAMILIES, INVALID_NUMBERS, PARSING, VALID_NUMBERS


def test_dataset_counts() -> None:
    assert len(VALID_NUMBERS) == 142
    assert len(INVALID_NUMBERS) == 107
    assert len(PARSING) == 16
    assert len(FAMILIES) == 31

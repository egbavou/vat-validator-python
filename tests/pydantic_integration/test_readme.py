"""Execute the documented country-aware model validator without rewriting it."""

import re
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from vat_number_validator import VatNumber


def test_country_model_validator_recipe() -> None:
    examples = re.findall(r"```python\n(.*?)```", Path("README.md").read_text(), flags=re.DOTALL)
    recipes = [example for example in examples if '@model_validator(mode="before")' in example]
    assert len(recipes) == 1
    namespace: dict[str, Any] = {}
    exec(compile(recipes[0], "README.md", "exec"), namespace)
    company = namespace["Company"]
    assert company.model_validate({"country": "FR", "vat_number": "27552032534"}).vat_number == VatNumber(
        "FR27552032534"
    )
    with pytest.raises(ValidationError):
        company.model_validate({"country": 123, "vat_number": "27552032534"})
    with pytest.raises(ValidationError):
        company.model_validate({"country": "FR", "vat_number": "28552032534"})

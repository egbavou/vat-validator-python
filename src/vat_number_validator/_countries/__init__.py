"""Canonical prefixes and cached rules, from PHP CountryRules.php."""

from ._base import CountryRule
from .austria import Austria
from .belgium import Belgium
from .bulgaria import Bulgaria
from .croatia import Croatia
from .cyprus import Cyprus
from .czechia import Czechia
from .denmark import Denmark
from .estonia import Estonia
from .finland import Finland
from .france import France
from .germany import Germany
from .greece import Greece
from .hungary import Hungary
from .ireland import Ireland
from .italy import Italy
from .latvia import Latvia
from .lithuania import Lithuania
from .luxembourg import Luxembourg
from .malta import Malta
from .netherlands import Netherlands
from .norway import Norway
from .poland import Poland
from .portugal import Portugal
from .romania import Romania
from .slovakia import Slovakia
from .slovenia import Slovenia
from .spain import Spain
from .sweden import Sweden
from .switzerland import Switzerland
from .united_kingdom import NorthernIreland, UnitedKingdom

_RULES: dict[str, type[CountryRule]] = {
    "AT": Austria,
    "BE": Belgium,
    "BG": Bulgaria,
    "CY": Cyprus,
    "CZ": Czechia,
    "DE": Germany,
    "DK": Denmark,
    "EE": Estonia,
    "EL": Greece,
    "ES": Spain,
    "FI": Finland,
    "FR": France,
    "HR": Croatia,
    "HU": Hungary,
    "IE": Ireland,
    "IT": Italy,
    "LT": Lithuania,
    "LU": Luxembourg,
    "LV": Latvia,
    "MT": Malta,
    "NL": Netherlands,
    "PL": Poland,
    "PT": Portugal,
    "RO": Romania,
    "SE": Sweden,
    "SI": Slovenia,
    "SK": Slovakia,
    "XI": NorthernIreland,
    "GB": UnitedKingdom,
    "CHE": Switzerland,
    "NO": Norway,
}
_instances: dict[str, CountryRule] = {}


def for_prefix(prefix: str) -> CountryRule | None:
    rule = _RULES.get(prefix)
    if rule is None:
        return None
    if prefix not in _instances:
        _instances[prefix] = rule()
    return _instances[prefix]


def prefix_for_country(country: str) -> str | None:
    prefix = {"GR": "EL", "CH": "CHE"}.get(country, country)
    return prefix if prefix in _RULES else None


def detect_prefix(value: str) -> tuple[str, int] | None:
    if value.startswith("CHE"):
        return "CHE", 3
    prefix = value[:2]
    canonical = "EL" if prefix == "GR" else prefix
    return (canonical, 2) if canonical in _RULES else None


def prefixes() -> list[str]:
    return list(_RULES)

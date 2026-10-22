import os

import pytest

django = pytest.importorskip("django")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.django_integration.settings")
django.setup()

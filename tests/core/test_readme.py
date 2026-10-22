"""Keep documented offline examples executable and repository links resolvable."""

import re
import subprocess
import sys
from pathlib import Path


def test_readme_examples() -> None:
    readme = Path("README.md").read_text()
    examples = re.findall(r"```python\n(.*?)```", readme, flags=re.DOTALL)
    assert examples, "README must provide Python examples"
    executed = 0
    for example in examples:
        compile(example, "README.md", "exec")
        if example.startswith("# Offline example"):
            subprocess.run([sys.executable, "-c", example], check=True)
            executed += 1
    assert executed > 0, "README must demonstrate offline validation"


def test_readme_local_links() -> None:
    readme = Path("README.md").read_text()
    for target in re.findall(r"\]\(([^)]+)\)", readme):
        if "://" not in target and not target.startswith("#"):
            assert Path(target.split("#", 1)[0]).is_file(), target

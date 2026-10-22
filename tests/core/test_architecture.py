import ast
import subprocess
import sys
from pathlib import Path


def test_core_import_is_independent() -> None:
    subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; import vat_number_validator; "
            "assert not any(n.split('.')[0] in {'httpx', 'django', 'pydantic'} for n in sys.modules)",
        ],
        check=True,
    )


def test_optional_import_locations() -> None:
    root = Path("src/vat_number_validator")
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text())
        parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports = [alias.name.split(".")[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and not node.level:
                imports = [(node.module or "").split(".")[0]]
            else:
                continue
            for name in imports:
                if name in ("django", "pydantic", "pydantic_core"):
                    assert path.name == "pydantic.py" or "django" in path.relative_to(root).parts, path
                if name == "httpx":
                    assert path.name in ("checkers.py", "_vies.py"), path
                    assert path.parent == root, path
                    ancestor: ast.AST = node
                    allowed = False
                    while ancestor in parents:
                        ancestor = parents[ancestor]
                        allowed |= isinstance(ancestor, (ast.FunctionDef, ast.AsyncFunctionDef)) or (
                            isinstance(ancestor, ast.If)
                            and isinstance(ancestor.test, ast.Name)
                            and ancestor.test.id == "TYPE_CHECKING"
                        )
                    assert allowed, (path, node.lineno)

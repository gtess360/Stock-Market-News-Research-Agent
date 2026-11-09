"""Initial automated tests for Phase 3.1 Project Setup."""
import importlib
from pathlib import Path
from streamlit.testing.v1 import AppTest


def test_core_dependencies_importable():
    """Verify that all core project technologies are installed and importable."""
    packages = [
        "streamlit",
        "langgraph",
        "openai",
        "plotly",
        "pydantic",
        "dotenv",
        "sqlite3",
        "pytest",
    ]
    for pkg in packages:
        mod = importlib.import_module(pkg)
        assert mod is not None, f"Failed to import package: {pkg}"


def test_project_structure_exists():
    """Verify that required directory structure is intact."""
    root = Path(__file__).resolve().parent.parent
    expected_dirs = ["src", "tests", "data", "config", "docs"]
    for d in expected_dirs:
        dir_path = root / d
        assert dir_path.is_dir(), f"Expected directory missing: {d}"


def test_required_configuration_files_exist():
    """Verify that configuration templates and gitignore exist."""
    root = Path(__file__).resolve().parent.parent
    assert (root / ".gitignore").is_file(), ".gitignore missing"
    assert (root / ".env.example").is_file(), ".env.example missing"
    assert (root / "requirements.txt").is_file(), "requirements.txt missing"


def test_src_package_version():
    """Verify that the src package is properly initialized."""
    import src
    assert hasattr(src, "__version__")
    assert src.__version__ == "0.1.0"


def test_app_entrypoint_callable():
    """Verify that the main app entrypoint function is defined and callable."""
    from src.app import main
    assert callable(main)


def test_streamlit_app_runtime_execution():
    """Verify that the Streamlit application foundation runs without uncaught exceptions."""
    root = Path(__file__).resolve().parent.parent
    app_file = str(root / "app.py")
    at = AppTest.from_file(app_file).run()
    assert not at.exception, f"AppTest threw unexpected exception: {at.exception}"
    assert len(at.title) >= 1
    assert "Stock Market News Research Agent" in at.title[0].value

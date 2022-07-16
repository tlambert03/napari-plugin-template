from pathlib import Path

import pytest


def test_manifest():
    """Test that the manifest is valid."""
    npe2 = pytest.importorskip("npe2")

    MANIFEST = Path(__file__).parent.parent / "napari.yaml"
    mf = npe2.PluginManifest.from_file(MANIFEST)
    mf.validate_imports()

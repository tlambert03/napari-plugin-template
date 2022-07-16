import os
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from subprocess import run
from typing import Any, Callable

import pytest
import tomli

TEMPLATE = Path(__file__).parent.parent


@contextmanager
def run_copier(template: Path, **kwargs: Any):
    with tempfile.TemporaryDirectory() as td:
        cmd = ["copier", "--force", str(template), str(td)]
        for k, v in kwargs.items():
            cmd.extend(["-d", f"{k}={v!r}"])
        run(cmd, check=True)
        yield Path(td)


@contextmanager
def inside_dir(dirpath):
    """
    Execute code from inside the given directory
    :param dirpath: String, path of the directory the command is being run.
    """
    old_path = os.getcwd()
    try:
        os.chdir(dirpath)
        yield
    finally:
        os.chdir(old_path)


@pytest.fixture(scope="session")
def template():
    with tempfile.TemporaryDirectory() as td:
        shutil.copytree(TEMPLATE, td, dirs_exist_ok=True)
        run(["git", "-C", td, "add", ".", "-A"])
        run(["git", "-C", td, "commit", "-m", "test"])
        run(["git", "-C", td, "tag", "99.99.99"])
        yield Path(td)


@pytest.fixture(scope="session")
def built(template):
    NAME = "some-project"
    with run_copier(
        template, plugin_name=NAME, full_name="Test Name", email="test@example.com"
    ) as out:
        with inside_dir(str(out)):
            gitcfg = out / ".git" / "config"
            gitcfg.touch()
            gitcfg.write_text("[user]\n\tname = Name\n\temail = email@wp.p\n")
            run(["git", "add", "."], check=True)
            run(["git", "commit", "-q", "-m", "initial"], check=True)
            yield out


def test_copier(template: Path):
    NAME = "some-project"
    with run_copier(
        template, full_name="Test Name", email="test@example.com", plugin_name=NAME
    ) as out:
        prj = tomli.loads((out / "pyproject.toml").read_text())["project"]
        assert prj["name"] == NAME
        assert prj["authors"] == [{"email": "test@example.com", "name": "Test Name"}]


def test_check_manifest(built):
    run(["check-manifest"], check=True)


def test_build(built):
    run(["python", "-m", "build"], check=True)
    assert len(list((built / "dist").iterdir())) == 2


def test_bake_and_pre_commit(built):
    run(["pre-commit", "autoupdate"], check=True)
    run(["pre-commit", "run", "--all-files"], check=True)


def test_bake_and_test(built):
    run(["tox", "--verbose"], check=True)

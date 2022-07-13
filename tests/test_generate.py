import os
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from re import TEMPLATE
from subprocess import run
from typing import Any, Callable

import pytest
import tomli

TEMPLATE = Path(__file__).parent.parent


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


@pytest.fixture
def copier(tmp_path: Path):
    def _copier(template: Path, dest: Path = tmp_path, **kwargs: Any):
        cmd = ["copier", "--force", str(template), str(dest)]
        for k, v in kwargs.items():
            cmd.extend(["-d", f"{k}={v!r}"])
        run(cmd, check=True)
        return tmp_path

    return _copier


def test_copier(template: Path, copier: Callable[..., Path]):
    NAME = "some-project"
    output = copier(
        template, full_name="Test Name", email="test@example.com", plugin_name=NAME
    )
    prj = tomli.loads((output / "pyproject.toml").read_text())["project"]
    assert prj["name"] == NAME
    assert prj["authors"] == [{"email": "test@example.com", "name": "Test Name"}]


# def test_bake_and_test(template: Path, copier: Callable[..., Path]):
#     NAME = "some-project"
#     output = copier(template, plugin_name=NAME)
#     run(["python", "-m", "pytest", str(output / "src" / "some_project")], check=True)


def test_bake_and_build(template, copier: Callable[..., Path]):
    output = copier(template, full_name="Test Name", email="test@example.com")

    with inside_dir(str(output)):
        run(["git", "init", "-q"], check=True)
        gitcfg = output / ".git" / "config"
        gitcfg.touch()
        gitcfg.write_text("[user]\n\tname = Name\n\temail = email@wp.p\n")
        run(["git", "add", "."], check=True)
        run(["git", "commit", "-q", "-m", "init"], check=True)
        run(["check-manifest"], check=True)
        run(["python", "-m", "build"], check=True)
        assert len(list((output / "dist").iterdir())) == 2


def test_bake_and_pre_commit(template, copier: Callable[..., Path]):
    output = copier(template)

    with inside_dir(str(output)):
        run(["git", "init", "-q"], check=True)
        run(["pre-commit", "autoupdate"], check=True)
        run(["pre-commit", "install"], check=True)
        run(["git", "add", "."], check=True)
        run(["pre-commit", "run", "--all-files"], check=True)

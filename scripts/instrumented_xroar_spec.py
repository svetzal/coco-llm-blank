"""The instrumented XRoar is patched only from pristine pinned source and rebuilt on any drift."""

import hashlib
import io
import shutil
import tarfile
from pathlib import Path
from unittest.mock import Mock

import instrumented_xroar as ix
import pytest
from instrumented_xroar import BuildHost, Edit, FilePatch
from native import ROOT

PRISTINE = b"int main(void) {\n\treturn 0;\n}\n"
PATCH = FilePatch(
    path="src/main.c",
    pristine_sha256=hashlib.sha256(PRISTINE).hexdigest(),
    edits=(Edit(anchor="\treturn 0;", replacement="\treturn 7;"),),
)
ARCHIVE = ROOT / "local/toolchain-sources" / f"xroar-{ix.VERSION}.tar.gz"


def archive_with(path: Path, files: dict[str, bytes]) -> Path:
    with tarfile.open(path, "w:gz") as tar:
        for name, data in files.items():
            info = tarfile.TarInfo(f"{ix.TREE}/{name}")
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return path


def compiling_host() -> Mock:
    """A host whose make writes an executable, as a real build would."""
    host = Mock(spec=BuildHost)
    host.which.side_effect = lambda name: f"/usr/bin/{name}"

    def run(command: list[str], cwd: Path, log: Path) -> None:
        log.write_text("ok\n")
        if command[0] == "make":
            (cwd / "src/xroar").write_bytes(b"executable")

    host.run.side_effect = run
    return host


@pytest.fixture
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    archive = archive_with(tmp_path / "xroar.tar.gz", {"src/main.c": PRISTINE})
    monkeypatch.setattr(ix, "cached_source", lambda name, root, download: archive)
    monkeypatch.setattr(ix, "recipe", lambda hooks=ix.HOOKS: (PATCH,))
    return tmp_path


class DescribePatching:
    def should_apply_each_edit_to_pristine_source(self) -> None:
        assert ix.apply(PATCH, PRISTINE) == PRISTINE.replace(b"return 0", b"return 7")

    def should_refuse_drifted_or_already_patched_source(self) -> None:
        patched = ix.apply(PATCH, PRISTINE)

        for source in (patched, PRISTINE + b"\n"):
            with pytest.raises(ValueError, match="not the pristine XRoar"):
                ix.apply(PATCH, source)

    @pytest.mark.parametrize("text,count", [("no anchor here", 0), ("ab ab", 2)])
    def should_require_exactly_one_anchor(self, text: str, count: int) -> None:
        with pytest.raises(ValueError, match=f"found {count}"):
            ix.replace_once(text, "ab" if count else "zz", "c", "src/x.c")

    def should_identify_the_patch_by_its_hooks(self, tmp_path: Path) -> None:
        hooks = tmp_path / "hooks"
        shutil.copytree(ix.HOOKS, hooks)
        before = ix.patch_digest(ix.recipe(hooks))

        (hooks / "video.c").write_text((hooks / "video.c").read_text() + "/* changed */\n")

        assert ix.patch_digest(ix.recipe(hooks)) != before
        assert ix.patch_digest(ix.recipe(ix.HOOKS)) == ix.patch_digest(ix.recipe())

    def should_read_key_names_from_the_keyboard_hook(self) -> None:
        names = ix.key_names()

        assert {"up", "down", "left", "right", "space", "enter", "a", "0"} <= set(names)
        assert len(names) == len(set(names))


class DescribeProvenance:
    def should_build_once_and_then_reuse_the_verified_executable(self, root: Path) -> None:
        host = compiling_host()
        said = []

        executable = ix.ensure(root, host, said.append)

        assert executable.read_bytes() == b"executable"
        assert "not built yet" in said[0]
        source = root / ix.HOME / ix.TREE / "src/main.c"
        assert source.read_bytes() == ix.apply(PATCH, PRISTINE)
        assert [call.args[0][0] for call in host.run.call_args_list] == ["./configure", "make"]
        host.reset_mock()
        assert ix.ensure(root, host, said.append) == executable
        assert not host.run.called and len(said) == 1

    @pytest.mark.parametrize(
        "damage,reason",
        [
            ("executable", "src/xroar no longer matches"),
            ("source", "src/main.c no longer matches"),
            ("record", "build record is unreadable"),
            ("patch", "hooks or patch changed"),
            ("archive", "pinned XRoar source changed"),
        ],
    )
    def should_rebuild_when_anything_recorded_changes(
        self, root: Path, monkeypatch: pytest.MonkeyPatch, damage: str, reason: str
    ) -> None:
        ix.ensure(root, compiling_host(), print)
        home = root / ix.HOME
        if damage == "executable":
            (home / ix.EXECUTABLE).write_bytes(b"substituted")
        elif damage == "source":
            (home / ix.TREE / "src/main.c").write_bytes(PRISTINE)
        elif damage == "record":
            (home / ix.RECORD).write_text("{}")
        elif damage == "patch":
            changed = PATCH.model_copy(update={"edits": (Edit(anchor="0", replacement="8"),)})
            monkeypatch.setattr(ix, "recipe", lambda hooks=ix.HOOKS: (changed,))
        else:
            monkeypatch.setattr(ix, "ARCHIVE_SHA256", "0" * 64)
        said = []

        ix.ensure(root, compiling_host(), said.append)

        assert reason in said[0]

    def should_explain_missing_build_tools_before_any_download(self, root: Path) -> None:
        host = Mock(spec=BuildHost)
        host.which.return_value = None

        with pytest.raises(ValueError, match="needs cc and make.*xcode-select --install"):
            ix.ensure(root, host, print)

        assert not host.download.called and not host.run.called
        assert not (root / ix.HOME).exists()

    def should_honour_compiler_overrides(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CC", "clang-19")
        host = Mock(spec=BuildHost)
        host.which.side_effect = lambda name: None if name == "clang-19" else name

        assert ix.missing_prerequisites(host) == ["cc"]

    def should_reject_a_build_that_does_not_verify(self, root: Path) -> None:
        host = compiling_host()
        host.run.side_effect = lambda command, cwd, log: log.write_text("no executable\n")

        with pytest.raises(FileNotFoundError):
            ix.ensure(root, host, print)

        assert not (root / ix.HOME / ix.RECORD).exists()

    def should_report_status_for_the_doctor(self, root: Path) -> None:
        host = compiling_host()

        assert "not built yet" in ix.status(root, host)
        assert "cc and make found" in ix.status(root, host)
        ix.ensure(root, host, print)
        assert ix.status(root, host).startswith("built and verified")
        host.which.side_effect = lambda name: None
        (root / ix.HOME / ix.RECORD).unlink()
        assert "missing cc, make" in ix.status(root, host)


class DescribeCommandLine:
    @pytest.mark.parametrize("arguments,code", [(["--help"], 0), ([], 2), (["status", "-x"], 2)])
    def should_parse_before_any_side_effect(self, arguments: list[str], code: int) -> None:
        host = Mock(spec=BuildHost)

        with pytest.raises(SystemExit) as error:
            ix.main(arguments, host)

        assert error.value.code == code
        assert not host.method_calls

    def should_report_failures_plainly(self, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
        def unavailable(root: Path, host: BuildHost) -> Path:
            raise ValueError("needs cc")

        monkeypatch.setattr(ix, "ensure", unavailable)

        assert ix.main(["build"], Mock(spec=BuildHost)) == 1

        assert "FAIL: needs cc" in capsys.readouterr().err

    def should_print_status(self, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
        monkeypatch.setattr(ix, "status", lambda root, host: "not built yet")

        assert ix.main(["status"], Mock(spec=BuildHost)) == 0

        assert capsys.readouterr().out == "not built yet\n"


@pytest.mark.integration
class DescribePinnedSource:
    @pytest.fixture
    def members(self) -> dict[str, bytes]:
        if not ARCHIVE.is_file():
            pytest.skip("The pinned XRoar archive is not cached in local/toolchain-sources")
        with tarfile.open(ARCHIVE) as tar:
            wanted = {f"{ix.TREE}/{p.path}" for p in ix.recipe()} | {f"{ix.TREE}/src/dkbd.h"}
            return {
                m.name.removeprefix(f"{ix.TREE}/"): tar.extractfile(m).read()
                for m in tar.getmembers()
                if m.name in wanted
            }

    def should_patch_every_pinned_file_exactly_once(self, members: dict[str, bytes]) -> None:
        for patch in ix.recipe():
            patched = ix.apply(patch, members[patch.path])

            assert patched != members[patch.path]
            with pytest.raises(ValueError, match="not the pristine"):
                ix.apply(patch, patched)

    def should_name_only_keys_xroar_defines(self, members: dict[str, bytes]) -> None:
        scan_codes = set(ix.re.findall(r"\b(DSCAN_\w+) =", members["src/dkbd.h"].decode()))
        used = set(ix.re.findall(r"DSCAN_\w+", ix.hook("keys.c")))

        assert used <= scan_codes

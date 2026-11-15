"""The instrumented XRoar applies its series only to the exact bytes it names, and rebuilds on drift."""

import difflib
import io
import re
import tarfile
from pathlib import Path
from unittest.mock import Mock

import instrumented_xroar as ix
import native
import pytest
from instrumented_xroar import BuildHost, Upstream
from native import ROOT

PRISTINE = b"int main(void) {\n\treturn 0;\n}\n"
PATCHED = b"int main(void) {\n\treturn 7;\n}\n"
HEADER = b"int answer(void);\n"
PIN = Upstream(
    version="9.9",
    tag="9.9",
    tag_commit="c" * 40,
    base_commit="c" * 40,
    git_url="https://fixture/xroar.git",
    archive_url="https://fixture/xroar-9.9.tar.gz",
    archive_sha256="0" * 64,
)


def patch_text(subject: str, files: dict[str, tuple[bytes | None, bytes]], context: int = 3) -> str:
    """A git format-patch file, with full blob hashes, for edits and new files."""
    text = (
        "From 0000000000000000000000000000000000000000 Mon Sep 17 00:00:00 2001\n"
        "From: Fixture <fixture@example.invalid>\n"
        f"Subject: [PATCH 1/1] {subject}\n\nWhy it changes.\n---\n"
    )
    for path, (old, new) in files.items():
        text += f"diff --git a/{path} b/{path}\n"
        if old is None:
            text += f"new file mode 100644\nindex {ix.EMPTY_BLOB}..{ix.git_blob(new)}\n"
        else:
            text += f"index {ix.git_blob(old)}..{ix.git_blob(new)} 100644\n"
        before = (old or b"").decode().splitlines(keepends=True)
        diff = difflib.unified_diff(before, new.decode().splitlines(keepends=True), n=context)
        lines = list(diff)[2:]
        text += f"--- {'/dev/null' if old is None else 'a/' + path}\n+++ b/{path}\n"
        text += "".join(lines)
    return text


def series_of(*texts: str) -> ix.Series:
    return ix.parse_series([(f"{n:04}-fixture.patch", t.encode()) for n, t in enumerate(texts)])


EDIT = patch_text(
    "Answer seven", {"src/main.c": (PRISTINE, PATCHED), "src/answer.h": (None, HEADER)}
)
SERIES = series_of(EDIT)


def tree(files: dict[str, bytes]):
    return lambda path: files.get(path)


def archive_with(path: Path, files: dict[str, bytes], top: str = PIN.tree) -> Path:
    with tarfile.open(path, "w:gz") as tar:
        for name, data in files.items():
            info = tarfile.TarInfo(f"{top}/{name}")
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return path


def compiling_host() -> Mock:
    """A host whose make writes an executable, as a real build would."""
    host = Mock(spec=BuildHost)
    host.which.side_effect = lambda name: f"/usr/bin/{name}"
    host.version.side_effect = lambda name: f"{name} (fixture) 1.0"

    def run(command: list[str], cwd: Path, log: Path) -> None:
        log.write_text("ok\n")
        if command[0] == "make":
            (cwd / "src/xroar").write_bytes(b"executable")

    host.run.side_effect = run
    return host


class DescribeSeries:
    def should_apply_edits_and_new_files_to_the_bytes_they_name(self) -> None:
        files = ix.apply_series(SERIES, tree({"src/main.c": PRISTINE}))

        assert files == {"src/main.c": PATCHED, "src/answer.h": HEADER}
        assert SERIES.patches[0].subject == "Answer seven"

    def should_apply_each_patch_on_top_of_the_ones_before(self) -> None:
        later = b"int main(void) {\n\treturn 8;\n}\n"
        series = series_of(EDIT, patch_text("Answer eight", {"src/main.c": (PATCHED, later)}))

        assert ix.apply_series(series, tree({"src/main.c": PRISTINE}))["src/main.c"] == later

    def should_insert_after_the_named_line_when_nothing_is_removed(self) -> None:
        grown = PRISTINE.replace(b"\treturn 0;\n", b"\treturn 0;\n\t/* done */\n")
        series = series_of(patch_text("Note", {"src/main.c": (PRISTINE, grown)}, context=0))

        assert ix.apply_series(series, tree({"src/main.c": PRISTINE}))["src/main.c"] == grown

    @pytest.mark.parametrize(
        "files,message",
        [
            ({"src/main.c": PATCHED}, "not the XRoar source this patch was made against"),
            ({"src/main.c": PRISTINE + b"\n"}, "not the XRoar source"),
            ({}, "missing from the XRoar source"),
            ({"src/main.c": PRISTINE, "src/answer.h": HEADER}, "already exists"),
        ],
    )
    def should_refuse_drifted_missing_or_already_patched_source(
        self, files: dict[str, bytes], message: str
    ) -> None:
        with pytest.raises(ValueError, match=message):
            ix.apply_series(SERIES, tree(files))

    def should_refuse_a_patch_whose_result_is_not_what_it_records(self) -> None:
        wrong = series_of(EDIT.replace("+\treturn 7;", "+\treturn 6;"))

        with pytest.raises(ValueError, match="did not give the bytes it records"):
            ix.apply_series(wrong, tree({"src/main.c": PRISTINE}))

    def should_refuse_a_hunk_that_does_not_match_its_source(self) -> None:
        wrong = series_of(EDIT.replace("-\treturn 0;", "-\treturn 1;"))

        with pytest.raises(ValueError, match="does not match the source"):
            ix.apply_series(wrong, tree({"src/main.c": PRISTINE}))

    @pytest.mark.parametrize(
        "change,message",
        [
            (lambda t: t.replace("index ", "rename from x\nindex ", 1), "unsupported change"),
            (lambda t: re.sub(r"index (\w{12})\w+", r"index \1", t, count=1), "--full-index"),
            (lambda t: t.replace("b/src/main.c\n@@", "b/../main.c\n@@"), "outside the XRoar"),
            (lambda t: t.replace("b/src/main.c\n@@", "b//etc/main.c\n@@"), "outside the XRoar"),
            (lambda t: t.replace("+++ b/src/main.c\n", ""), r"no \+\+\+ line"),
            (lambda t: t.replace("Subject: ", "Topic: "), "no Subject line"),
            (lambda t: t.split("diff --git")[0], "no file changes"),
            (lambda t: t.replace(" }\n", ""), "truncated or malformed"),
            (lambda t: t.replace("@@ -0,0", "@@ zero"), "unexpected line"),
            (lambda t: t + "\ntrailing words\n", "unexpected text after the last hunk"),
        ],
    )
    def should_refuse_unsupported_or_malformed_patches(self, change, message: str) -> None:
        with pytest.raises(ValueError, match=message):
            series_of(change(EDIT))

    def should_refuse_an_empty_series(self) -> None:
        with pytest.raises(ValueError, match="series is empty"):
            ix.parse_series([])

    def should_ignore_a_format_patch_signature(self) -> None:
        signed = series_of(EDIT + "-- \n2.50.0\n\n")

        assert signed.patches == SERIES.patches

    def should_identify_the_series_by_name_order_and_bytes(self) -> None:
        first, second = (b"one", b"two")

        digests = {
            ix.series_digest([("a.patch", first), ("b.patch", second)]),
            ix.series_digest([("b.patch", second), ("a.patch", first)]),
            ix.series_digest([("a.patch", first), ("c.patch", second)]),
            ix.series_digest([("a.patch", first), ("b.patch", b"two!")]),
        }

        assert len(digests) == 4

    def should_read_the_committed_series_against_the_pinned_tag(self) -> None:
        pin, series = ix.load_pin(), ix.load_series()

        assert [p.name[:4] for p in series.patches] == ["0001", "0002", "0003", "0004"]
        assert pin.tree == f"xroar-{pin.version}"
        assert native.SOURCES["xroar"] == (pin.version, pin.archive_url, pin.archive_sha256)

    def should_read_key_names_from_the_series(self) -> None:
        names = ix.key_names(ix.load_series())

        assert {"up", "down", "left", "right", "space", "enter", "a", "0"} <= set(names)
        assert len(names) == len(set(names))


class DescribeProvenance:
    @pytest.fixture
    def root(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
        archive = archive_with(tmp_path / "xroar.tar.gz", {"src/main.c": PRISTINE})
        pin = PIN.model_copy(update={"archive_sha256": ix.sha256(archive.read_bytes())})
        monkeypatch.setattr(ix, "cached_source", lambda name, root, download: archive)
        monkeypatch.setattr(ix, "load_pin", lambda: pin)
        monkeypatch.setattr(ix, "load_series", lambda: SERIES)
        return tmp_path

    def should_build_once_and_then_reuse_the_verified_executable(self, root: Path) -> None:
        host = compiling_host()
        said = []

        executable = ix.ensure(root, host, said.append)

        assert executable.read_bytes() == b"executable"
        assert "9.9 (not built yet)" in said[0]
        tree = root / ix.HOME / PIN.tree
        assert (tree / "src/main.c").read_bytes() == PATCHED
        assert (tree / "src/answer.h").read_bytes() == HEADER
        commands = [call.args[0][0] for call in host.run.call_args_list]
        assert commands == ["autoreconf", "./configure", "make"]
        record = ix.Provenance.model_validate_json((root / ix.HOME / ix.RECORD).read_text())
        assert record.series_sha256 == SERIES.digest and record.upstream_version == "9.9"
        assert record.tools["automake"] == "automake (fixture) 1.0"
        host.reset_mock()
        assert ix.ensure(root, host, said.append) == executable
        assert not host.run.called and len(said) == 1

    @pytest.mark.parametrize(
        "damage,reason",
        [
            ("executable", "src/xroar no longer matches"),
            ("source", "src/main.c no longer matches"),
            ("new file", "src/answer.h no longer matches"),
            ("record", "build record is unreadable"),
            ("series", "patch series changed"),
            ("pin", "pinned XRoar release changed"),
        ],
    )
    def should_notice_when_anything_recorded_changes(
        self, root: Path, monkeypatch: pytest.MonkeyPatch, damage: str, reason: str
    ) -> None:
        ix.ensure(root, compiling_host(), print)
        home = root / ix.HOME
        if damage == "executable":
            (home / PIN.tree / "src/xroar").write_bytes(b"substituted")
        elif damage == "source":
            (home / PIN.tree / "src/main.c").write_bytes(PRISTINE)
        elif damage == "new file":
            (home / PIN.tree / "src/answer.h").unlink()
        elif damage == "record":
            (home / ix.RECORD).write_text("{}")
        elif damage == "series":
            changed = series_of(EDIT.replace("Why it changes.", "Why it changed."))
            monkeypatch.setattr(ix, "load_series", lambda: changed)
        else:
            moved = ix.load_pin().model_copy(update={"version": "9.9.1"})
            monkeypatch.setattr(ix, "load_pin", lambda: moved)

        assert reason in ix.stale_reason(home, ix.load_pin(), ix.load_series())

    def should_rebuild_a_damaged_build_on_next_use(self, root: Path) -> None:
        ix.ensure(root, compiling_host(), print)
        (root / ix.HOME / PIN.tree / "src/xroar").write_bytes(b"substituted")
        said = []

        executable = ix.ensure(root, compiling_host(), said.append)

        assert "src/xroar no longer matches" in said[0]
        assert executable.read_bytes() == b"executable"

    def should_refuse_an_archive_that_does_not_match_the_pin(self, root: Path) -> None:
        archive = archive_with(root / "other.tar.gz", {"src/main.c": PATCHED})

        with pytest.raises(ValueError, match="does not match the pinned XRoar 9.9 checksum"):
            ix.build(compiling_host(), ix.load_pin(), SERIES, archive, root / "home")

    def should_refuse_an_archive_for_a_different_release(self, root: Path) -> None:
        archive = archive_with(root / "other.tar.gz", {"src/main.c": PRISTINE}, top="xroar-1.0")
        pin = PIN.model_copy(update={"archive_sha256": ix.sha256(archive.read_bytes())})

        with pytest.raises(ValueError, match="does not unpack to xroar-9.9/"):
            ix.build(compiling_host(), pin, SERIES, archive, root / "home")

    def should_explain_missing_build_tools_before_any_download(self, root: Path) -> None:
        host = Mock(spec=BuildHost)
        host.which.side_effect = lambda name: None if name in ("automake", "pkg-config") else name

        with pytest.raises(ValueError, match="needs automake, pkg-config, which are not") as error:
            ix.ensure(root, host, print)

        assert "brew install autoconf automake pkgconf" in str(error.value)
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
        assert "build tools found" in ix.status(root, host)
        ix.ensure(root, host, print)
        assert ix.status(root, host).startswith("built and verified")
        host.which.side_effect = lambda name: None
        (root / ix.HOME / ix.RECORD).unlink()
        assert "missing cc, make, autoreconf" in ix.status(root, host)


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
        pin = ix.load_pin()
        archive = ROOT / "local/toolchain-sources" / f"{pin.tree}.tar.gz"
        if not archive.is_file():
            pytest.skip("The pinned XRoar archive is not cached in local/toolchain-sources")
        with tarfile.open(archive) as tar:
            return {
                m.name.removeprefix(f"{pin.tree}/"): tar.extractfile(m).read()
                for m in tar.getmembers()
                if m.isfile()
            }

    def should_apply_the_series_exactly_once(self, members: dict[str, bytes]) -> None:
        series = ix.load_series()

        patched = ix.apply_series(series, members.get)

        assert all(patched[path] != members.get(path) for path in patched)
        with pytest.raises(ValueError, match="already|not the XRoar source"):
            ix.apply_series(series, (members | patched).get)

    def should_name_only_keys_xroar_defines(self, members: dict[str, bytes]) -> None:
        scan_codes = set(re.findall(r"\b(DSCAN_\w+) =", members["src/dkbd.h"].decode()))
        used = set(re.findall(r"DSCAN_\w+", ix.load_series().text))

        assert used <= scan_codes

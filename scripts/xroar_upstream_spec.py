"""A release is adopted only after its rebased series built and its captures were compared."""

import json
import subprocess
from pathlib import Path
from unittest.mock import Mock

import instrumented_xroar as ix
import pytest
import xroar_upstream as xu
from instrumented_xroar import BuildHost, Upstream
from xroar_upstream import CheckRun, Trial, UpstreamHost

PIN = Upstream(
    version="1.12.1",
    tag="1.12.1",
    tag_commit="d" * 40,
    base_commit="d" * 40,
    git_url="https://fixture/xroar.git",
    archive_url="https://fixture/xroar-1.12.1.tar.gz",
    archive_sha256="a" * 64,
)
PATCH = min(ix.PATCHES.glob("*.patch")).read_bytes()
LS_REMOTE = (
    "aaaa\trefs/tags/1.9\nbbbb\trefs/tags/1.10\ncccc\trefs/tags/1.12.1\n"
    "dddd\trefs/tags/1.13\neeee\trefs/tags/1.13^{}\nffff\trefs/tags/debian/1.2\n"
)
PAGE = '<a href="xroar-1.12.1.tar.gz">x</a> <a href="xroar-1.13-w64.zip">w</a> xroar-1.13.tar.gz'


def provenance(version: str = "1.13") -> ix.Provenance:
    return ix.Provenance(
        upstream_version=version,
        tag=version,
        tag_commit="e" * 40,
        base_commit="e" * 40,
        archive_url=f"https://fixture/xroar-{version}.tar.gz",
        archive_sha256="b" * 64,
        series=["0001-fixture.patch"],
        series_sha256="c" * 64,
        patched_sha256={},
        commands={},
        tools={},
        executable=f"xroar-{version}/src/xroar",
        executable_sha256="f" * 64,
        host="Fixture",
    )


def check(**changes) -> CheckRun:
    values = {
        "example": "examples/first-screen",
        "arguments": ["--video"],
        "exit_codes": {"pinned": 0, "pinned-again": 0, "1.13": 0},
        "deterministic": True,
        "identical": ["main-coco1-1.png"],
        "different": [],
        "missing": [],
        "extra": [],
    }
    return CheckRun(**(values | changes))


class DescribeReleases:
    def should_order_release_numbers_and_ignore_other_names(self) -> None:
        names = ["1.13", "1.9", "1.10", "1.12.1", "1.13-rc1", "debian/1.2", "1.12.1"]

        assert xu.releases(names) == ["1.9", "1.10", "1.12.1", "1.13"]

    def should_read_upstream_tags_and_archives(self) -> None:
        assert xu.tags_listed(LS_REMOTE) == ["1.9", "1.10", "1.12.1", "1.13"]
        assert xu.archives_listed(PAGE) == ["1.12.1", "1.13"]

    def should_say_how_far_behind_the_pin_is(self) -> None:
        lines = xu.report_lines(
            PIN, ["1.12.1", "1.13", "1.14"], ["1.13"], ("/bin/xroar", "XRoar 1.13")
        )

        assert "Behind by 2 releases: 1.13, 1.14" in lines[4]
        assert lines[4].endswith("trial 1.14")
        assert lines[5] == "Ordinary XRoar: /bin/xroar is 1.13; it differs from the pin 1.12.1."

    @pytest.mark.parametrize(
        "tags,archives,status",
        [
            (["1.12.1"], ["1.12.1"], "Up to date"),
            (None, ["1.13"], "Behind by 1 release: 1.13."),
            (None, None, "could not be read"),
            ([], [], "could not be read"),
        ],
    )
    def should_report_each_source_and_survive_one_failing(self, tags, archives, status) -> None:
        lines = xu.report_lines(PIN, tags, archives, None)

        assert status in lines[4]
        assert ("unavailable" in lines[2]) == (tags is None)
        assert lines[5].startswith("Ordinary XRoar: not found")

    def should_say_when_the_ordinary_xroar_matches_the_pin(self) -> None:
        line = xu.stock_line(PIN, ("/opt/homebrew/bin/xroar", "XRoar 1.12.1"))

        assert line.endswith("is 1.12.1; it matches the pin.")
        assert "is unknown" in xu.stock_line(PIN, ("/x", "something else"))


class DescribeComparison:
    def should_sort_files_by_how_they_compare(self) -> None:
        before = {"a.ram": b"1", "b.png": b"2", "c.wav": b"3"}
        after = {"a.ram": b"1", "b.png": b"X", "d.log": b"4"}

        assert xu.compare(before, after) == {
            "identical": ["a.ram"],
            "different": ["b.png"],
            "missing": ["c.wav"],
            "extra": ["d.log"],
        }

    def should_ignore_only_the_emulator_path_in_result_records(self) -> None:
        record = {"variants": {"main": {"emulator": "/a/xroar", "frames": [1]}}, "list": [{}]}
        moved = json.dumps(
            {**record, "variants": {"main": {"emulator": "/b/xroar", "frames": [1]}}}
        )
        changed = json.dumps({**record, "variants": {"main": {"emulator": "/a", "frames": [2]}}})
        before = {"r.json": json.dumps(record).encode()}

        assert xu.compare(before, {"r.json": moved.encode()})["identical"] == ["r.json"]
        assert xu.compare(before, {"r.json": changed.encode()})["different"] == ["r.json"]

    def should_require_the_pinned_build_to_repeat_itself(self) -> None:
        same = {"a.ram": b"1"}
        captures = {"pinned": same, "pinned-again": {"a.ram": b"2"}, "1.13": same}

        run = xu.check_run("examples/x", (), captures, {"pinned": 0}, "1.13")

        assert not run.deterministic and not run.passed
        assert run.identical == ["a.ram"]

    def should_not_call_an_empty_capture_repeatable(self) -> None:
        run = xu.check_run(
            "examples/x", (), {"pinned": {}, "pinned-again": {}, "1.13": {}}, {}, "1.13"
        )

        assert not run.deterministic

    @pytest.mark.parametrize(
        "checks,expected",
        [
            ([check()], "identical"),
            ([check(), check(different=["main-coco1-1.png"])], "different"),
            ([check(extra=["new.log"])], "different"),
            ([check(exit_codes={"pinned": 0, "1.13": 1})], "failed"),
            ([check(deterministic=False)], "failed"),
        ],
    )
    def should_give_a_verdict(self, checks: list[CheckRun], expected: str) -> None:
        assert xu.verdict(checks) == expected

    def should_summarise_a_trial_for_the_operator(self) -> None:
        trial = Trial(
            pin=PIN,
            application="clean",
            series=["0001-fixture.patch"],
            series_sha256="c" * 64,
            build=provenance(),
            checks=[check(different=["main-coco1-1.png"]), check(deterministic=False)],
            verdict="failed",
        )

        lines = xu.summary(trial)

        assert lines[0].startswith("XRoar 1.12.1: series clean; built xroar-1.13/src/xroar")
        assert "    differs: main-coco1-1.png" in lines
        assert any(line.endswith("the pinned build was not repeatable") for line in lines)
        assert lines[-1] == "Verdict: failed."


class DescribeReport:
    def should_print_the_report_and_succeed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(ix, "load_pin", lambda: PIN)
        host = Mock(spec=UpstreamHost)
        host.git.return_value = LS_REMOTE
        host.fetch_text.return_value = PAGE
        host.stock_xroar.return_value = None
        said = []

        assert xu.report(host, said.append) == 0

        assert "Behind by 1 release: 1.13." in said[4]
        host.git.assert_called_once_with(["ls-remote", "--tags", PIN.git_url])

    def should_fail_when_no_source_can_be_read(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(ix, "load_pin", lambda: PIN)
        host = Mock(spec=UpstreamHost)
        host.git.side_effect = subprocess.CalledProcessError(128, "git")
        host.fetch_text.side_effect = OSError("offline")
        host.stock_xroar.return_value = None

        assert xu.report(host, print) == 1


class FakeGit:
    """Plays the git commands a trial runs: clone, am, rev-parse and format-patch."""

    def __init__(self, conflict: bool = False, broken: bool = False) -> None:
        self.conflict = conflict
        self.broken = broken
        self.based = True
        self.commands: list[list[str]] = []

    def git(self, arguments: list[str], cwd: Path | None = None) -> str:
        self.commands.append(arguments)
        if arguments[0] == "clone":
            Path(arguments[-1], ".git").mkdir(parents=True)
        if arguments[0] == "format-patch":
            out = Path(arguments[arguments.index("-o") + 1])
            out.mkdir(parents=True)
            (out / "0001-null-render-frames.patch").write_bytes(PATCH)
        if arguments[0] == "rev-parse":
            return ("b" if arguments[1].startswith("cafe") else "e") * 40 + "\n"
        if arguments[:2] == ["log", "-1"]:
            return "trap: press scripted keys\n"
        if arguments[0] == "diff":
            return "src/xroar.c\n"
        return ""

    def git_succeeds(self, arguments: list[str], cwd: Path) -> bool:
        self.commands.append(arguments)
        if arguments[0] == "am":
            return not self.broken
        if arguments[0] == "merge-base":
            return self.based
        if self.conflict:
            (cwd / ".git/rebase-merge").mkdir()
        return not self.conflict


def trial_host(
    conflict: bool = False, differ: bool = False, broken: bool = False
) -> tuple[Mock, FakeGit]:
    fake = FakeGit(conflict, broken)
    host = Mock(spec=UpstreamHost)
    host.git.side_effect = fake.git
    host.git_succeeds.side_effect = fake.git_succeeds
    host.download.side_effect = lambda url, destination: destination.write_bytes(b"archive")

    def run_check(example: Path, arguments: list[str], xroar: Path, log: Path) -> int:
        output = example.parents[1] / "build" / example.name
        output.mkdir(parents=True, exist_ok=True)
        picture = b"new" if differ and "1.13" in str(xroar) else b"old"
        (output / "main-coco1-1.png").write_bytes(picture)
        log.write_text("PASS\n")
        return 0

    host.check.side_effect = run_check
    return host, fake


class DescribeTrial:
    @pytest.fixture
    def root(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
        monkeypatch.setattr(ix, "load_pin", lambda: PIN)

        def build_verified(builder, pin, series, archive, home, say) -> Path:
            archive()
            home.mkdir(parents=True, exist_ok=True)
            (home / ix.RECORD).write_text(provenance(pin.version).model_dump_json())
            return home / "trial-xroar-1.13"

        monkeypatch.setattr(ix, "build_verified", build_verified)
        monkeypatch.setattr(ix, "ensure", lambda root, builder, say: root / "pinned-xroar")
        return tmp_path

    def should_rebase_build_and_compare_in_the_lab(self, root: Path) -> None:
        host, fake = trial_host()

        trial = xu.run_trial(root, "1.13", host, Mock(spec=BuildHost), say=print)

        lab = root / "local/lab/xroar-1.13"
        assert trial.verdict == "identical" and trial.application == "clean"
        assert trial.pin.tag_commit == "e" * 40
        assert trial.pin.archive_sha256 == ix.sha256(b"archive")
        assert trial.pin.archive_url.endswith("/xroar/dl/xroar-1.13.tar.gz")
        assert [c.example for c in trial.checks] == [e for e, _ in xu.EQUIVALENCE]
        assert Trial.model_validate_json((lab / "trial.json").read_text()) == trial
        assert "XRoar 1.13" in (lab / "LAB.md").read_text()
        assert (lab / "captures/1.13/first-screen/main-coco1-1.png").read_bytes() == b"old"
        am = next(c for c in fake.commands if c[0] == "am")
        assert all(a.endswith(".patch") for a in am[2:])
        assert ["checkout", "--quiet", "-b", xu.BRANCH, f"{'d' * 40}^{{commit}}"] in fake.commands
        rebase = next(c for c in fake.commands if c[0] == "rebase")
        assert rebase[2:5] == ["--onto", "1.13^{commit}", f"{'d' * 40}^{{commit}}"]
        export = next(c for c in fake.commands if c[0] == "format-patch")
        assert export[-1] == f"{'e' * 40}..{xu.BRANCH}"
        assert ["config", "user.email", "coco-starter@example.invalid"] in fake.commands

    def should_report_differences_without_failing(self, root: Path) -> None:
        host, _ = trial_host(differ=True)

        trial = xu.run_trial(root, "1.13", host, Mock(spec=BuildHost), say=print)

        assert trial.verdict == "different"
        assert trial.checks[0].different == ["main-coco1-1.png"]

    def should_stop_at_a_conflict_and_resume_after_it_is_resolved(self, root: Path) -> None:
        host, fake = trial_host(conflict=True)

        with pytest.raises(
            ValueError, match="'trap: press scripted keys' conflicts in src/xroar.c"
        ):
            xu.run_trial(root, "1.13", host, Mock(spec=BuildHost), say=print)

        lab = root / "local/lab/xroar-1.13"
        (lab / "xroar/.git/rebase-merge").rmdir()
        trial = xu.run_trial(root, "1.13", host, Mock(spec=BuildHost), say=print)
        assert trial.application == "resolved by hand"
        assert sum(c[0] == "rebase" for c in fake.commands) == 1

    def should_refuse_a_series_that_does_not_fit_its_own_tag(self, root: Path) -> None:
        host, fake = trial_host(broken=True)

        with pytest.raises(ValueError, match="does not apply to its pinned base d+"):
            xu.run_trial(root, "1.13", host, Mock(spec=BuildHost), say=print)

        assert ["am", "--abort"] in fake.commands

    def should_fetch_an_existing_clone_and_rebase_afresh_on_request(self, root: Path) -> None:
        host, fake = trial_host()
        xu.run_trial(root, "1.13", host, Mock(spec=BuildHost), say=print)

        xu.run_trial(root, "1.13", host, Mock(spec=BuildHost), fresh=True, say=print)

        assert ["fetch", "--quiet", "--tags", "origin"] in fake.commands
        assert sum(c[0] == "am" for c in fake.commands) == 2

    def should_rebase_onto_a_named_base_when_the_archive_is_newer_than_the_tag(
        self, root: Path
    ) -> None:
        host, fake = trial_host()

        trial = xu.run_trial(root, "1.13", host, Mock(spec=BuildHost), base="cafe", say=print)

        assert (trial.pin.tag, trial.pin.tag_commit) == ("1.13", "e" * 40)
        assert trial.pin.base_commit == "b" * 40
        rebase = next(c for c in fake.commands if c[0] == "rebase")
        assert rebase[3] == "cafe^{commit}"
        export = next(c for c in fake.commands if c[0] == "format-patch")
        assert export[-1] == f"{'b' * 40}..{xu.BRANCH}"

    def should_refuse_a_lab_branch_not_on_the_named_base(self, root: Path) -> None:
        host, fake = trial_host()
        xu.run_trial(root, "1.13", host, Mock(spec=BuildHost), say=print)
        fake.based = False

        with pytest.raises(ValueError, match="is not based on cafe"):
            xu.run_trial(root, "1.13", host, Mock(spec=BuildHost), base="cafe", say=print)

    def should_refuse_an_archive_with_another_checksum(self, root: Path) -> None:
        host, _ = trial_host()

        with pytest.raises(ValueError, match="not the 0+ you gave"):
            xu.run_trial(root, "1.13", host, Mock(spec=BuildHost), expected="0" * 64)

    def should_refuse_a_name_that_is_not_a_release(self, root: Path) -> None:
        with pytest.raises(ValueError, match="not an XRoar release number"):
            xu.run_trial(root, "../1.13", Mock(spec=UpstreamHost), Mock(spec=BuildHost))


class DescribeAdopt:
    @pytest.fixture
    def root(self, tmp_path: Path) -> Path:
        lab = tmp_path / "local/lab/xroar-1.13"
        (lab / "series").mkdir(parents=True)
        (lab / "series/0001-rebased.patch").write_bytes(PATCH)
        (lab / "xroar-1.13.tar.gz").write_bytes(b"archive")
        patches = tmp_path / "patches"
        patches.mkdir()
        (patches / "0001-old.patch").write_text("old")
        (patches / ix.PIN).write_text(PIN.model_dump_json())
        return tmp_path

    def write_trial(self, root: Path, verdict: str = "identical") -> Trial:
        lab = root / "local/lab/xroar-1.13"
        trial = Trial(
            pin=PIN.model_copy(
                update={"version": "1.13", "tag": "1.13", "archive_sha256": ix.sha256(b"archive")}
            ),
            application="clean",
            series=["0001-rebased.patch"],
            series_sha256=ix.load_series(lab / "series").digest,
            build=provenance(),
            checks=[check()],
            verdict=verdict,
        )
        (lab / "trial.json").write_text(trial.model_dump_json())
        return trial

    def should_write_the_tested_series_and_pin(self, root: Path) -> None:
        trial = self.write_trial(root)
        patches = root / "patches"

        xu.adopt(root, "1.13", trial.pin.archive_sha256, False, patches, print)

        assert sorted(p.name for p in patches.glob("*.patch")) == ["0001-rebased.patch"]
        assert ix.load_pin(patches) == trial.pin
        cached = root / "local/toolchain-sources/xroar-1.13.tar.gz"
        assert cached.read_bytes() == b"archive"

    def should_accept_differences_only_when_asked(self, root: Path) -> None:
        trial = self.write_trial(root, "different")
        patches = root / "patches"

        with pytest.raises(ValueError, match="Explain each difference"):
            xu.adopt(root, "1.13", trial.pin.archive_sha256, False, patches, print)

        assert (patches / "0001-old.patch").exists()
        xu.adopt(root, "1.13", trial.pin.archive_sha256, True, patches, print)
        assert not (patches / "0001-old.patch").exists()

    @pytest.mark.parametrize(
        "damage,message",
        [
            ("no trial", "run trial first"),
            ("failed", "trial failed"),
            ("checksum", "is not the trial archive's"),
            ("series", "changed after the trial"),
        ],
    )
    def should_refuse_what_was_not_tested(self, root: Path, damage: str, message: str) -> None:
        trial = self.write_trial(root, "failed" if damage == "failed" else "identical")
        lab = root / "local/lab/xroar-1.13"
        confirmed = "0" * 64 if damage == "checksum" else trial.pin.archive_sha256
        if damage == "no trial":
            (lab / "trial.json").unlink()
        if damage == "series":
            (lab / "series/0001-rebased.patch").write_bytes(PATCH.replace(b"null:", b"Null:"))

        with pytest.raises(ValueError, match=message):
            xu.adopt(root, "1.13", confirmed, False, root / "patches", print)

        assert (root / "patches/0001-old.patch").read_text() == "old"


class DescribeCommandLine:
    @pytest.mark.parametrize(
        "arguments,code",
        [(["--help"], 0), ([], 2), (["trial"], 2), (["adopt", "1.13"], 2), (["report", "-x"], 2)],
    )
    def should_parse_before_any_side_effect(self, arguments: list[str], code: int) -> None:
        host, builder = Mock(spec=UpstreamHost), Mock(spec=BuildHost)

        with pytest.raises(SystemExit) as error:
            xu.main(arguments, host, builder)

        assert error.value.code == code
        assert not host.method_calls and not builder.method_calls

    @pytest.mark.parametrize("verdict,code", [("identical", 0), ("different", 3), ("failed", 1)])
    def should_exit_with_the_trial_verdict(
        self, monkeypatch: pytest.MonkeyPatch, capsys, verdict: str, code: int
    ) -> None:
        trial = Trial(
            pin=PIN,
            application="clean",
            series=[],
            series_sha256="c" * 64,
            build=provenance(),
            checks=[],
            verdict=verdict,
        )
        monkeypatch.setattr(xu, "run_trial", lambda *args, **kwargs: trial)

        assert xu.main(["trial", "1.13"], Mock(spec=UpstreamHost), Mock(spec=BuildHost)) == code

        assert f"Verdict: {verdict}." in capsys.readouterr().out

    def should_dispatch_report_and_adopt(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls = []
        monkeypatch.setattr(xu, "report", lambda host: calls.append("report") or 0)
        monkeypatch.setattr(xu, "adopt", lambda *args: calls.append(args[1:]))

        xu.main(["report"], Mock(spec=UpstreamHost), Mock(spec=BuildHost))
        xu.main(
            ["adopt", "1.13", "--sha256", "abc", "--accept-differences"],
            Mock(spec=UpstreamHost),
            Mock(spec=BuildHost),
        )

        assert calls == ["report", ("1.13", "abc", True)]

    def should_report_failures_plainly(self, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
        def refuse(*args) -> None:
            raise ValueError("The XRoar 1.13 trial failed")

        monkeypatch.setattr(xu, "adopt", refuse)

        code = xu.main(
            ["adopt", "1.13", "--sha256", "x"], Mock(spec=UpstreamHost), Mock(spec=BuildHost)
        )

        assert code == 1
        assert "FAIL: The XRoar 1.13 trial failed" in capsys.readouterr().err


class DescribeLabFiles:
    def should_keep_only_files_a_check_wrote(self, tmp_path: Path) -> None:
        (tmp_path / "stale.ram").write_bytes(b"old")
        before = {"stale.ram": (tmp_path / "stale.ram").stat().st_mtime_ns}
        (tmp_path / "main-coco1-1.ram").write_bytes(b"new")

        assert xu.captured(tmp_path, before) == {"main-coco1-1.ram": b"new"}

    def should_give_lab_clones_a_neutral_identity_without_owner_hooks(self, tmp_path: Path) -> None:
        host = Mock(spec=UpstreamHost)
        (tmp_path / ".git").mkdir()

        xu.configure_lab_clone(tmp_path, host)

        settings = {call.args[0][1]: call.args[0][2] for call in host.git.call_args_list}
        assert settings["core.hooksPath"] == str(tmp_path / ".git/no-hooks")
        assert settings["user.name"] == "CoCo starter"

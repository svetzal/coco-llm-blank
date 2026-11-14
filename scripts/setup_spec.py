"""Setup behavior through its command and real download boundaries."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest
import setup
from references import ConversionError, ConvertedPage, DoclingGateway, Resource, conversion_profile


class DescribeProjectSetup:
    @pytest.mark.parametrize("target", list(setup.TARGETS))
    def should_preserve_owner_notes_and_reject_a_target_change(
        self, project: Path, target: str
    ) -> None:
        assert setup.main(["--target", target, "--guidance-only"], project) == 0
        notes = project / "local/PROJECT.md"
        notes.write_text(notes.read_text() + "\nOwner notes.\n")
        saved = notes.read_bytes()

        assert setup.main(["--guidance-only"], project) == 0
        other = "coco3" if target != "coco3" else "coco1"
        assert setup.main(["--guidance-only", "--target", other], project) == 1

        assert notes.read_bytes() == saved

    @pytest.mark.parametrize("suffix", [" (owner request)", "", "   "])
    def should_preserve_an_annotated_target_without_a_final_newline(
        self, project: Path, suffix: str
    ) -> None:
        notes = project / "local/PROJECT.md"
        notes.parent.mkdir()
        notes.write_text("# My project\nTarget: CoCo 1" + suffix)
        saved = notes.read_bytes()

        assert setup.main(["--guidance-only", "--target", "coco1"], project) == 0
        assert setup.main(["--guidance-only"], project) == 0
        assert setup.main(["--guidance-only", "--target", "coco2"], project) == 1
        assert notes.read_bytes() == saved

    @pytest.mark.parametrize(
        "target_lines",
        [
            "Target: CoCo 10",
            "Target: unknown",
            "No target yet",
            "Target: CoCo 1\nTarget: CoCo 2",
            "Target: CoCo 1\nTarget: CoCo 1",
        ],
    )
    def should_explain_an_invalid_or_ambiguous_target(
        self, project: Path, target_lines: str, capsys: pytest.CaptureFixture[str]
    ) -> None:
        notes = project / "local/PROJECT.md"
        notes.parent.mkdir()
        notes.write_text(target_lines)

        assert setup.main(["--guidance-only"], project) == 1
        assert "needs one Target line" in capsys.readouterr().err
        assert notes.read_text() == target_lines

    def should_use_the_owners_interactive_target(self, project: Path) -> None:
        console = Mock(spec=setup.ConsoleGateway)
        console.choose_target.return_value = "coco3"

        result = setup.main(["--guidance-only"], project, console=console)

        assert result == 0
        assert "Target: CoCo 3" in (project / "local/PROJECT.md").read_text()

    def should_explain_a_missing_target_without_a_traceback(
        self, project: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        console = Mock(spec=setup.ConsoleGateway)
        console.choose_target.side_effect = ValueError(
            "Choose a target with --target coco1, coco2, or coco3"
        )

        result = setup.main(["--guidance-only"], project, console=console)

        assert result == 1
        assert "Choose a target" in capsys.readouterr().err
        assert not (project / "local").exists()

    @pytest.mark.parametrize("value", ["invalid", "0:1", "2:1"])
    def should_reject_invalid_page_ranges_before_creating_notes(
        self, project: Path, value: str
    ) -> None:
        assert setup.main(["--pages", value], project) == 1
        assert not (project / "local").exists()

    @pytest.mark.parametrize("arguments", [["--list"], ["--resource", "unknown"]])
    def should_not_initialize_when_listing_or_rejecting_a_selection(
        self, project: Path, arguments: list[str]
    ) -> None:
        expected = 0 if arguments == ["--list"] else 1
        assert setup.main(arguments, project) == expected
        assert not (project / "local").exists()

    def should_report_damaged_resources_as_unconverted(self, project: Path) -> None:
        directory = project / "local/references/test-book"
        directory.mkdir(parents=True)
        (directory / "source.pdf").write_bytes(b"corrupted")

        result = setup.main(["--target", "coco1"], project)

        assert result == 1
        assert "not converted" in (project / "local/INDEX.md").read_text()

    def should_keep_failed_conversions_unconverted(self, project: Path, pdf_bytes: bytes) -> None:
        directory = project / "local/references/test-book"
        directory.mkdir(parents=True)
        (directory / "source.pdf").write_bytes(pdf_bytes)
        documents = Mock(spec=DoclingGateway)
        documents.page_count.return_value = 2
        documents.profile.return_value = conversion_profile()
        documents.convert_page.side_effect = ConversionError("model unavailable")

        result = setup.main(["--target", "coco1"], project, documents=documents)

        assert result == 1
        assert "not converted" in (project / "local/INDEX.md").read_text()

    def should_convert_only_requested_resources_and_index_all_of_them(
        self,
        project: Path,
        resource: Resource,
        pdf_bytes: bytes,
    ) -> None:
        other = resource.model_copy(update={"id": "other-book"})
        (project / "resources.json").write_text(
            json.dumps([resource.model_dump(), other.model_dump()])
        )
        directory = project / "local/references/other-book"
        directory.mkdir(parents=True)
        (directory / "source.pdf").write_bytes(pdf_bytes)
        documents = Mock(spec=DoclingGateway)
        documents.page_count.return_value = 2
        documents.profile.return_value = conversion_profile()
        documents.convert_page.return_value = ConvertedPage(
            markdown="selected content", document={}
        )

        result = setup.main(
            ["--target", "coco2", "--resource", "other-book", "--pages", "1:1"],
            project,
            documents=documents,
        )

        assert result == 0
        assert not (project / "local/references/test-book").exists()
        assert "selected content" in (directory / "text.md").read_text()
        index = (project / "local/INDEX.md").read_text()
        assert "--resource test-book" in index
        assert "references/other-book/text.md" in index

    @pytest.mark.parametrize("damage", ["source", "metadata", "legacy"])
    def should_not_advertise_stale_or_legacy_outputs(
        self,
        project: Path,
        resource: Resource,
        pdf_bytes: bytes,
        damage: str,
    ) -> None:
        directory = project / "local/references/test-book"
        directory.mkdir(parents=True)
        (directory / "source.pdf").write_bytes(pdf_bytes)
        documents = Mock(spec=DoclingGateway)
        documents.page_count.return_value = 2
        documents.profile.return_value = conversion_profile()
        documents.convert_page.return_value = ConvertedPage(markdown="content", document={})
        assert (
            setup.main(["--target", "coco2", "--pages", "1:1"], project, documents=documents) == 0
        )
        metadata = directory / "extraction.json"
        record = json.loads(metadata.read_text())
        if damage == "source":
            (directory / "source.pdf").write_bytes(b"damaged")
        elif damage == "metadata":
            record["sha256"] = "0" * 64
        else:
            del record["profile"]
        metadata.write_text(json.dumps(record))

        assert setup.main(["--guidance-only"], project) == 0

        assert "not converted" in (project / "local/INDEX.md").read_text()

    def should_report_unreadable_manifest(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert setup.main(["--list"], tmp_path) == 1
        assert "Setup failed" in capsys.readouterr().err

    def should_run_the_script_entry_point(self) -> None:
        result = subprocess.run(
            [sys.executable, str(Path(setup.__file__)), "--list"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0
        assert "6809-programming" in result.stdout


class DescribeManifestValidation:
    @pytest.mark.parametrize(
        "change",
        [
            {"id": "../outside"},
            {"url": "http://example.com/book.pdf"},
            {"sha256": ""},
            {"title": ""},
        ],
    )
    def should_reject_unsafe_or_incomplete_resources(
        self, project: Path, resource: Resource, change: dict[str, str]
    ) -> None:
        data = resource.model_dump() | change
        (project / "resources.json").write_text(json.dumps([data]))

        with pytest.raises(ValueError):
            setup.ProjectStore(project).resources()

    def should_reject_duplicate_identifiers(self, project: Path, resource: Resource) -> None:
        (project / "resources.json").write_text(json.dumps([resource.model_dump()] * 2))

        with pytest.raises(ValueError, match="Duplicate"):
            setup.ProjectStore(project).resources()


class DescribeReferenceDownloads:
    def should_reuse_a_verified_pdf_even_when_its_server_is_unavailable(
        self,
        tmp_path: Path,
        resource: Resource,
        pdf_server: str,
        pdf_bytes: bytes,
    ) -> None:
        gateway = setup.DownloadGateway()
        destination = tmp_path / "reference.pdf"
        remote = resource.model_copy(update={"url": pdf_server + "/reference.pdf"})
        gateway.fetch(remote, destination)
        cached = remote.model_copy(update={"url": pdf_server + "/missing"})

        gateway.fetch(cached, destination)

        assert destination.read_bytes() == pdf_bytes

    def should_reject_a_corrupted_cached_pdf(self, tmp_path: Path, resource: Resource) -> None:
        destination = tmp_path / "reference.pdf"
        destination.write_bytes(b"corrupted")

        with pytest.raises(ValueError, match="checksum mismatch"):
            setup.DownloadGateway().fetch(resource, destination)

        assert destination.read_bytes() == b"corrupted"

    @pytest.mark.parametrize("failure", ["missing", "checksum", "invalid"])
    def should_leave_no_partial_files_after_a_failed_download(
        self,
        tmp_path: Path,
        resource: Resource,
        pdf_server: str,
        failure: str,
    ) -> None:
        changes = {"url": pdf_server + ("/missing" if failure == "missing" else "/reference.pdf")}
        if failure == "checksum":
            changes["sha256"] = "0" * 64
        elif failure == "invalid":
            changes = {
                "url": pdf_server + "/invalid",
                "sha256": hashlib.sha256(b"not a PDF").hexdigest(),
            }
        remote = resource.model_copy(update=changes)

        with pytest.raises((OSError, ValueError)):
            setup.DownloadGateway().fetch(remote, tmp_path / "reference.pdf")

        assert list(tmp_path.iterdir()) == []

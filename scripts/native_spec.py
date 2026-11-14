"""Native installation tests keep system changes behind the host gateway."""

import hashlib
import io
import subprocess
import tarfile
from pathlib import Path
from unittest.mock import Mock

import native
import pytest


@pytest.fixture
def isolated_tools(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("PATH", str(tmp_path / "bin"))
    for variable in ("LWASM", "LWLINK", "XROAR"):
        monkeypatch.delenv(variable, raising=False)
    return tmp_path


def provide(root: Path, *names: str) -> None:
    for name in names:
        path = root / "local/toolchain/bin" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("#!/bin/sh\nexit 0\n")
        path.chmod(0o755)


class DescribeNativeInstallation:
    @pytest.mark.parametrize(
        "system,machine", [("Darwin", "arm64"), ("Linux", "x86_64"), ("Linux", "aarch64")]
    )
    def should_reuse_existing_tools_without_system_changes(
        self, isolated_tools: Path, system: str, machine: str
    ) -> None:
        provide(isolated_tools, "lwasm", "lwlink", "xroar")
        host = Mock(spec=native.HostGateway)
        host.system.return_value = system
        host.machine.return_value = machine
        native.install(isolated_tools, host)
        host.run.assert_not_called()
        host.dependencies.assert_not_called()

    def should_install_only_missing_mac_packages(self, isolated_tools: Path) -> None:
        provide(isolated_tools, "xroar")
        host = Mock(spec=native.HostGateway)
        host.system.return_value = "Darwin"
        host.machine.return_value = "arm64"
        host.brew.return_value = "brew"

        def install(command: list[str]) -> None:
            assert command == ["brew", "install", "lwtools"]
            provide(isolated_tools, "lwasm", "lwlink")

        host.run.side_effect = install
        native.install(isolated_tools, host)
        assert native.tool_path("lwasm", isolated_tools)
        assert native.tool_path("lwlink", isolated_tools)

    @pytest.mark.parametrize("machine", ["x86_64", "i386", "unknown"])
    @pytest.mark.parametrize("tools_present", [False, True])
    def should_reject_non_arm64_macos_before_installation(
        self, isolated_tools: Path, machine: str, tools_present: bool
    ) -> None:
        if tools_present:
            provide(isolated_tools, "lwasm", "lwlink", "xroar")
        host = Mock(spec=native.HostGateway)
        host.system.return_value = "Darwin"
        host.machine.return_value = machine

        with pytest.raises(ValueError, match="Intel Macs are unsupported"):
            native.install(isolated_tools, host)

        host.brew.assert_not_called()
        host.run.assert_not_called()
        host.download.assert_not_called()
        host.dependencies.assert_not_called()
        assert not (isolated_tools / "local/toolchain-sources").exists()

    def should_not_hide_a_broken_override(
        self, isolated_tools: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        provide(isolated_tools, "lwasm", "lwlink", "xroar")
        monkeypatch.setenv("LWASM", "/missing/assembler")
        with pytest.raises(ValueError, match="LWASM"):
            native.install(isolated_tools, Mock(spec=native.HostGateway))

    def should_reject_unsupported_hosts(self, isolated_tools: Path) -> None:
        host = Mock(spec=native.HostGateway)
        host.system.return_value = "Windows"
        with pytest.raises(ValueError, match="macOS and Ubuntu"):
            native.install(isolated_tools, host)
        host.run.assert_not_called()

    def should_detect_an_install_that_did_not_supply_tools(self, isolated_tools: Path) -> None:
        host = Mock(spec=native.HostGateway)
        host.system.return_value = "Darwin"
        host.machine.return_value = "arm64"
        host.brew.return_value = "brew"
        with pytest.raises(ValueError, match="not discoverable"):
            native.install(isolated_tools, host)

    def should_report_unsupported_macos_through_the_entry_point(
        self, monkeypatch: pytest.MonkeyPatch, capsys
    ) -> None:
        monkeypatch.setattr(native.platform, "system", lambda: "Darwin")
        monkeypatch.setattr(native.platform, "machine", lambda: "x86_64")
        discovery = Mock(side_effect=AssertionError("host rejection must precede tool discovery"))
        monkeypatch.setattr(native, "tool_path", discovery)

        assert native.main() == 1

        error = capsys.readouterr().err
        assert "Intel Macs are unsupported" in error
        assert "native arm64 terminal and Python" in error
        discovery.assert_not_called()

    def should_report_permission_failure(self, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
        monkeypatch.setattr(
            native, "install", Mock(side_effect=subprocess.CalledProcessError(1, "sudo"))
        )
        assert native.main() == 1
        assert "approval" in capsys.readouterr().err


class DescribeVerifiedSourceBuild:
    @pytest.mark.parametrize("name", ["lwtools", "xroar"])
    def should_build_verified_sources_and_reuse_the_download(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str
    ) -> None:
        stream = io.BytesIO()
        files = {
            "configure": "#!/bin/sh\nexit 0\n",
            "Makefile": (
                "all:\n\t@true\ninstall:\n\tmkdir -p $(PREFIX)/bin\n"
                f"\tprintf '#!/bin/sh\\nexit 0\\n' > $(PREFIX)/bin/{name}\n"
                f"\tchmod +x $(PREFIX)/bin/{name}\n"
            ),
        }
        with tarfile.open(fileobj=stream, mode="w:gz") as archive:
            for filename, text in files.items():
                member = tarfile.TarInfo(f"{name}-1/{filename}")
                member.size = len(text.encode())
                member.mode = 0o755
                archive.addfile(member, io.BytesIO(text.encode()))
        data = stream.getvalue()
        monkeypatch.setitem(
            native.SOURCES, name, ("1", "https://fixture/source", hashlib.sha256(data).hexdigest())
        )
        host = Mock(spec=native.HostGateway)
        host.download.side_effect = lambda url, path: path.write_bytes(data)
        host.run.side_effect = native.HostGateway().run

        native.build_source(name, tmp_path, host)
        native.build_source(name, tmp_path, host)

        assert (tmp_path / "local/toolchain/bin" / name).is_file()
        assert host.download.call_count == 1
        cached = tmp_path / f"local/toolchain-sources/{name}-1.tar.gz"
        cached.write_bytes(b"corrupt")
        with pytest.raises(ValueError, match="cached source checksum"):
            native.build_source(name, tmp_path, host)

    def should_not_publish_a_bad_download(self, tmp_path: Path) -> None:
        host = Mock(spec=native.HostGateway)
        host.download.side_effect = lambda url, path: path.write_bytes(b"not the source")
        with pytest.raises(ValueError, match="source checksum"):
            native.build_source("lwtools", tmp_path, host)
        assert not list((tmp_path / "local/toolchain-sources").glob("*.tar.gz"))


class DescribeHostGateway:
    def should_fetch_bytes_and_propagate_command_failure(self, tmp_path: Path) -> None:
        source = tmp_path / "source"
        source.write_bytes(b"local source fixture")
        destination = tmp_path / "download"
        host = native.HostGateway()
        host.download(source.as_uri(), destination)
        assert destination.read_bytes() == source.read_bytes()
        with pytest.raises(subprocess.CalledProcessError):
            host.run(["/bin/sh", "-c", "exit 7"])
        assert host.system()

    @pytest.mark.parametrize(
        "release, expected",
        [
            ({"ID": "ubuntu", "VERSION_ID": "24.04"}, True),
            ({"ID": "ubuntu", "VERSION_ID": "22.04"}, False),
            ({"ID": "debian", "VERSION_ID": "12"}, False),
        ],
    )
    def should_limit_linux_installation_to_the_supported_release(
        self, monkeypatch: pytest.MonkeyPatch, release, expected
    ) -> None:
        monkeypatch.setattr(native.platform, "freedesktop_os_release", lambda: release)
        assert native.HostGateway().ubuntu_supported() is expected

    def should_preserve_a_host_manager_on_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        brew = tmp_path / "brew"
        brew.write_text("#!/bin/sh\nexit 0\n")
        brew.chmod(0o755)
        monkeypatch.setenv("PATH", str(tmp_path))
        assert native.HostGateway().brew() == str(brew)

    @pytest.mark.parametrize("uid, prefix", [(0, []), (1000, ["sudo", "-n"])])
    def should_fail_fast_when_system_installation_is_denied(
        self, monkeypatch: pytest.MonkeyPatch, uid, prefix
    ) -> None:
        monkeypatch.setattr(native.os, "geteuid", lambda: uid)
        host = native.HostGateway()
        host.run = Mock(side_effect=[None, subprocess.CalledProcessError(1, "apt-get")])
        with pytest.raises(subprocess.CalledProcessError):
            host.dependencies()
        assert host.run.call_args_list[-1].args[0][: len(prefix)] == prefix

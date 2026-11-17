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
    monkeypatch.setattr(native, "HOMEBREW_BIN", tmp_path / "brew/bin")
    for variable in native.VARIABLES.values():
        monkeypatch.delenv(variable, raising=False)
    return tmp_path


def provide(root: Path, *names: str) -> None:
    for name in names:
        path = root / "local/toolchain/bin" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("#!/bin/sh\nexit 0\n")
        path.chmod(0o755)


INSTALLED = "\tmkdir -p $(PREFIX)/bin\n\tprintf '#!/bin/sh\\nexit 0\\n' > $(PREFIX)/bin/{tool}\n\tchmod +x $(PREFIX)/bin/{tool}\n"


def source_archive(name: str, tool: str) -> bytes:
    """An original release archive laid out as the named package's build expects."""
    if name == "toolshed":
        # ToolShed's makefile lives in build/unix and takes a lowercase prefix.
        rule = INSTALLED.replace("$(PREFIX)", "$(prefix)").format(tool=tool)
        files = {"build/unix/Makefile": f"all:\n\t@true\ninstall:\n{rule}"}
    else:
        rule = INSTALLED.format(tool=tool)
        files = {"configure": "#!/bin/sh\nexit 0\n", "Makefile": f"all:\n\t@true\ninstall:\n{rule}"}
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w:gz") as archive:
        for filename, text in files.items():
            member = tarfile.TarInfo(f"{name}-1/{filename}")
            member.size = len(text.encode())
            member.mode = 0o755
            archive.addfile(member, io.BytesIO(text.encode()))
    return stream.getvalue()


def system_path(monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    """Keep the isolated tool folder first, and let real builds find make and the shell."""
    monkeypatch.setenv("PATH", f"{root / 'bin'}:/usr/bin:/bin")


def pin_source(monkeypatch: pytest.MonkeyPatch, name: str, data: bytes) -> None:
    monkeypatch.setitem(
        native.SOURCES, name, ("1", "https://fixture/source", hashlib.sha256(data).hexdigest())
    )


class DescribeNativeInstallation:
    @pytest.mark.parametrize(
        "system,machine", [("Darwin", "arm64"), ("Linux", "x86_64"), ("Linux", "aarch64")]
    )
    def should_reuse_existing_tools_without_system_changes(
        self, isolated_tools: Path, system: str, machine: str
    ) -> None:
        provide(isolated_tools, "lwasm", "lwlink", "decb")
        host = Mock(spec=native.HostGateway)
        host.system.return_value = system
        host.machine.return_value = machine
        native.install(isolated_tools, host)
        host.run.assert_not_called()
        host.dependencies.assert_not_called()

    def should_install_only_missing_mac_packages(self, isolated_tools: Path) -> None:
        provide(isolated_tools, "decb")
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

    def should_build_toolshed_from_its_pinned_source_on_a_mac(
        self, isolated_tools: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        system_path(monkeypatch, isolated_tools)
        provide(isolated_tools, "lwasm", "lwlink")
        data = source_archive("toolshed", "decb")
        pin_source(monkeypatch, "toolshed", data)
        host = Mock(spec=native.HostGateway)
        host.system.return_value = "Darwin"
        host.machine.return_value = "arm64"
        host.has_build_tools.return_value = True
        host.download.side_effect = lambda url, path: path.write_bytes(data)
        host.run.side_effect = native.HostGateway().run

        native.install(isolated_tools, host)

        assert native.tool_path("decb", isolated_tools) == str(
            isolated_tools / "local/toolchain/bin/decb"
        )
        host.brew.assert_not_called()

    def should_explain_missing_compilers_without_stopping_setup(
        self, isolated_tools: Path, capsys
    ) -> None:
        host = Mock(spec=native.HostGateway)
        host.system.return_value = "Darwin"
        host.machine.return_value = "arm64"
        host.brew.return_value = "brew"
        host.has_build_tools.return_value = False
        host.run.side_effect = lambda command: provide(isolated_tools, "lwasm", "lwlink")

        native.install(isolated_tools, host)

        assert native.tool_path("lwasm", isolated_tools)
        assert not native.tool_path("decb", isolated_tools)
        host.download.assert_not_called()
        error = capsys.readouterr().err
        assert "ToolShed was not installed" in error and "xcode-select --install" in error

    def should_report_a_failed_toolshed_build_without_stopping_setup(
        self, isolated_tools: Path, capsys
    ) -> None:
        provide(isolated_tools, "lwasm", "lwlink")
        host = Mock(spec=native.HostGateway)
        host.system.return_value = "Linux"
        host.machine.return_value = "x86_64"
        host.ubuntu_supported.return_value = True
        host.has_build_tools.return_value = True
        host.download.side_effect = lambda url, path: path.write_bytes(b"not the release")

        native.install(isolated_tools, host)

        assert "ToolShed was not installed: toolshed: source checksum" in capsys.readouterr().err

    def should_report_a_toolshed_build_that_supplied_no_decb(
        self, isolated_tools: Path, monkeypatch: pytest.MonkeyPatch, capsys
    ) -> None:
        system_path(monkeypatch, isolated_tools)
        provide(isolated_tools, "lwasm", "lwlink")
        data = source_archive("toolshed", "os9")
        pin_source(monkeypatch, "toolshed", data)
        host = Mock(spec=native.HostGateway)
        host.system.return_value = "Darwin"
        host.machine.return_value = "arm64"
        host.has_build_tools.return_value = True
        host.download.side_effect = lambda url, path: path.write_bytes(data)
        host.run.side_effect = native.HostGateway().run

        native.install(isolated_tools, host)

        assert "decb is not discoverable" in capsys.readouterr().err

    def should_build_every_missing_package_on_ubuntu(
        self, isolated_tools: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        archives = {
            "lwtools": source_archive("lwtools", "lwasm"),
            "toolshed": source_archive("toolshed", "decb"),
        }
        for name, data in archives.items():
            pin_source(monkeypatch, name, data)
        system_path(monkeypatch, isolated_tools)
        provide(isolated_tools, "lwlink")
        host = Mock(spec=native.HostGateway)
        host.system.return_value = "Linux"
        host.machine.return_value = "x86_64"
        host.ubuntu_supported.return_value = True
        host.has_build_tools.return_value = True
        downloads = iter(archives.values())
        host.download.side_effect = lambda url, path: path.write_bytes(next(downloads))
        host.run.side_effect = native.HostGateway().run

        native.install(isolated_tools, host)

        host.dependencies.assert_called_once()
        assert native.tool_path("lwasm", isolated_tools)
        assert native.tool_path("decb", isolated_tools)

    @pytest.mark.parametrize("machine", ["x86_64", "i386", "unknown"])
    @pytest.mark.parametrize("tools_present", [False, True])
    def should_reject_non_arm64_macos_before_installation(
        self, isolated_tools: Path, machine: str, tools_present: bool
    ) -> None:
        if tools_present:
            provide(isolated_tools, "lwasm", "lwlink", "decb")
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
        provide(isolated_tools, "lwasm", "lwlink", "decb")
        monkeypatch.setenv("LWASM", "/missing/assembler")
        with pytest.raises(ValueError, match="LWASM"):
            native.install(isolated_tools, Mock(spec=native.HostGateway))

    def should_install_what_the_xroar_build_lacks_with_homebrew(self, isolated_tools: Path) -> None:
        provide(isolated_tools, "lwasm", "lwlink", "decb")
        present = {"autoreconf", "pkg-config"}
        host = Mock(spec=native.HostGateway)
        host.system.return_value = "Darwin"
        host.machine.return_value = "arm64"
        host.brew.return_value = "brew"
        host.has_command.side_effect = lambda name: name in present
        host.has_library.side_effect = lambda name: name in present
        host.run.side_effect = lambda command: present.update({"automake", "sdl2"})

        native.install(isolated_tools, host)

        host.run.assert_called_once_with(["brew", "install", "automake", "sdl2"])

    def should_install_lwtools_and_the_xroar_build_needs_in_one_homebrew_call(
        self, isolated_tools: Path
    ) -> None:
        provide(isolated_tools, "decb")
        host = Mock(spec=native.HostGateway)
        host.system.return_value = "Darwin"
        host.machine.return_value = "arm64"
        host.brew.return_value = "brew"
        host.has_command.return_value = True
        host.has_library.side_effect = [False, True]
        host.run.side_effect = lambda command: provide(isolated_tools, "lwasm", "lwlink")

        native.install(isolated_tools, host)

        host.run.assert_called_once_with(["brew", "install", "lwtools", "sdl2"])

    def should_install_ubuntu_packages_when_only_the_xroar_build_lacks_something(
        self, isolated_tools: Path
    ) -> None:
        provide(isolated_tools, "lwasm", "lwlink", "decb")
        host = Mock(spec=native.HostGateway)
        host.system.return_value = "Linux"
        host.machine.return_value = "x86_64"
        host.ubuntu_supported.return_value = True
        host.has_command.side_effect = [False, True, True, True, True, True]
        host.has_library.return_value = True

        native.install(isolated_tools, host)

        host.dependencies.assert_called_once()
        host.download.assert_not_called()

    def should_stop_when_the_xroar_build_still_lacks_something(self, isolated_tools: Path) -> None:
        provide(isolated_tools, "lwasm", "lwlink", "decb")
        host = Mock(spec=native.HostGateway)
        host.system.return_value = "Darwin"
        host.machine.return_value = "arm64"
        host.brew.return_value = "brew"
        host.has_command.return_value = True
        host.has_library.return_value = False

        with pytest.raises(ValueError, match="the XRoar build still lacks sdl2"):
            native.install(isolated_tools, host)

    def should_reject_unsupported_hosts(self, isolated_tools: Path) -> None:
        host = Mock(spec=native.HostGateway)
        host.system.return_value = "Windows"
        with pytest.raises(ValueError, match="macOS and Ubuntu"):
            native.install(isolated_tools, host)
        host.run.assert_not_called()

    def should_detect_an_install_that_did_not_supply_tools(self, isolated_tools: Path) -> None:
        provide(isolated_tools, "decb")
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
    @pytest.mark.parametrize("name", ["lwtools", "toolshed"])
    def should_build_verified_sources_and_reuse_the_download(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str
    ) -> None:
        data = source_archive(name, name)
        pin_source(monkeypatch, name, data)
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

    def should_install_every_ubuntu_package_the_xroar_build_needs(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(native.os, "geteuid", lambda: 0)
        host = native.HostGateway()
        host.run = Mock()

        host.dependencies()

        installed = host.run.call_args_list[-1].args[0]
        for package in ("build-essential", "autoconf", "automake", "pkg-config", "libsdl2-dev"):
            assert package in installed
        assert {"libasound2-dev", "libpulse-dev"} <= set(installed)

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


class DescribeBuildToolDiscovery:
    @pytest.fixture
    def commands(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
        monkeypatch.setenv("PATH", str(tmp_path))
        return tmp_path

    def command(self, directory: Path, name: str, status: int = 0) -> None:
        path = directory / name
        path.write_text(f"#!/bin/sh\nexit {status}\n")
        path.chmod(0o755)

    @pytest.mark.parametrize("status,expected", [(0, True), (2, False)])
    def should_ask_xcode_select_on_a_mac(
        self, commands: Path, monkeypatch: pytest.MonkeyPatch, status: int, expected: bool
    ) -> None:
        monkeypatch.setattr(native.platform, "system", lambda: "Darwin")
        self.command(commands, "cc")
        self.command(commands, "make")
        self.command(commands, "xcode-select", status)

        assert native.HostGateway().has_build_tools() is expected

    def should_not_trust_mac_stubs_without_xcode_select(
        self, commands: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(native.platform, "system", lambda: "Darwin")
        self.command(commands, "cc")
        self.command(commands, "make")

        assert native.HostGateway().has_build_tools() is False

    def should_need_both_a_compiler_and_make_on_linux(
        self, commands: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(native.platform, "system", lambda: "Linux")
        self.command(commands, "cc")

        assert native.HostGateway().has_build_tools() is False

        self.command(commands, "make")

        assert native.HostGateway().has_build_tools() is True


class DescribeXRoarBuildDiscovery:
    @pytest.fixture
    def commands(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
        monkeypatch.setenv("PATH", str(tmp_path))
        monkeypatch.setattr(native.platform, "system", lambda: "Linux")
        return tmp_path

    def should_find_commands_and_ask_pkg_config_for_libraries(self, commands: Path) -> None:
        host = native.HostGateway()

        assert not host.has_command("automake")
        assert not host.has_library("sdl2")

        pkg_config = commands / "pkg-config"
        pkg_config.write_text('#!/bin/sh\n[ "$2" = sdl2 ]\n')
        pkg_config.chmod(0o755)

        assert host.has_command("pkg-config")
        assert host.has_library("sdl2")
        assert not host.has_library("gtk+-3.0")

    @pytest.mark.parametrize(
        "path,system,machine,expected",
        [
            ("/usr/bin", "Darwin", "arm64", "/usr/bin:/opt/homebrew/bin"),
            ("/opt/homebrew/bin:/usr/bin", "Darwin", "arm64", "/opt/homebrew/bin:/usr/bin"),
            ("", "Darwin", "arm64", "/opt/homebrew/bin"),
            ("/usr/bin", "Linux", "aarch64", "/usr/bin"),
            ("/usr/bin", "Darwin", "x86_64", "/usr/bin"),
        ],
    )
    def should_add_apple_silicon_homebrew_to_the_search_path(
        self, path: str, system: str, machine: str, expected: str
    ) -> None:
        assert native.search_path(path, system, machine) == expected


class DescribeHomebrewDiscovery:
    def should_discover_new_homebrew_tools_without_shell_reload(self, isolated_tools, monkeypatch):
        monkeypatch.setattr(native.platform, "system", lambda: "Darwin")
        monkeypatch.setattr(native.platform, "machine", lambda: "arm64")
        assert native.tool_path("lwasm", isolated_tools) is None
        native.HOMEBREW_BIN.mkdir(parents=True)
        for name in ("lwasm", "lwlink", "decb"):
            executable = native.HOMEBREW_BIN / name
            executable.write_text("#!/bin/sh\nexit 0\n")
            executable.chmod(0o755)
            assert native.tool_path(name, isolated_tools) == str(executable)
            subprocess.run([native.tool_path(name, isolated_tools)], check=True)
        host = Mock(spec=native.HostGateway)
        host.system.return_value = "Darwin"
        host.machine.return_value = "arm64"
        native.install(isolated_tools, host)
        host.run.assert_not_called()
        host.brew.assert_not_called()
        provide(isolated_tools, "lwasm")
        assert native.tool_path("lwasm", isolated_tools) == str(
            isolated_tools / "local/toolchain/bin/lwasm"
        )
        monkeypatch.setenv("LWASM", "/missing/explicit")
        assert native.tool_path("lwasm", isolated_tools) is None

    @pytest.mark.parametrize("system,machine", [("Linux", "aarch64"), ("Darwin", "x86_64")])
    def should_not_use_apple_silicon_prefix_on_other_hosts(
        self, isolated_tools, monkeypatch, system, machine
    ):
        monkeypatch.setattr(native.platform, "system", lambda: system)
        monkeypatch.setattr(native.platform, "machine", lambda: machine)
        native.HOMEBREW_BIN.mkdir(parents=True)
        executable = native.HOMEBREW_BIN / "lwasm"
        executable.write_text("#!/bin/sh\nexit 0\n")
        executable.chmod(0o755)
        assert native.tool_path("lwasm", isolated_tools) is None

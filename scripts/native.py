"""Install the assembly and disk tools, and what the XRoar build needs, on Apple Silicon macOS
or Ubuntu 24.04.

XRoar itself is built from the pin by scripts/instrumented_xroar.py.
"""

import hashlib
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOMEBREW_BIN = Path("/opt/homebrew/bin")
SOURCES = {
    "lwtools": (
        "4.25",
        "https://www.lwtools.ca/releases/lwtools/lwtools-4.25.tar.gz",
        "9bb97e987d486d7abd85d04cb98a53f666f02785c108647b795c4a111c5eb09f",
    ),
    # Homebrew has no ToolShed formula, so both hosts build this release.
    "toolshed": (
        "2.6.1",
        "https://github.com/nitros9project/toolshed/archive/refs/tags/v2.6.1.tar.gz",
        "99f0bb23f14b7d0c4b69b7fa0b846ee31e042e4e81ac8f8586064b45855854d2",
    ),
}
# Each tool's override variable, in the order the doctor reports them.
VARIABLES = {"lwasm": "LWASM", "lwlink": "LWLINK", "decb": "DECB"}
# The source release that supplies each tool.
PACKAGES = {"lwasm": "lwtools", "lwlink": "lwtools", "decb": "toolshed"}
# What the XRoar build needs besides a C compiler and make, with the Homebrew formula and the
# Ubuntu package that supply it. instrumented_xroar.py checks the same names before it builds.
XROAR_COMMANDS = {
    "autoreconf": ("autoconf", "autoconf"),
    "automake": ("automake", "automake"),
    "pkg-config": ("pkgconf", "pkg-config"),
}
# Libraries found through pkg-config. SDL2 gives XRoar its window and sound on both hosts.
XROAR_LIBRARIES = {"sdl2": ("sdl2", "libsdl2-dev")}
# Ubuntu packages for XRoar's PNG screenshots and its ALSA and PulseAudio sound modules.
XROAR_EXTRAS = ("libpng-dev", "libpulse-dev", "libasound2-dev")


def tool_path(name: str, root: Path = ROOT) -> str | None:
    """Honor overrides, project tools, PATH, then Apple Silicon Homebrew."""
    variable = VARIABLES[name]
    if variable in os.environ:
        return shutil.which(os.environ[variable])
    local = root / "local/toolchain/bin" / name
    return shutil.which(str(local)) or shutil.which(name, path=host_path())


def search_path(path: str, system: str, machine: str) -> str:
    """PATH with Apple Silicon Homebrew appended, for a shell that has not loaded it yet."""
    folders = path.split(os.pathsep) if path else []
    if system == "Darwin" and machine == "arm64" and str(HOMEBREW_BIN) not in folders:
        folders.append(str(HOMEBREW_BIN))
    return os.pathsep.join(folders)


def host_path() -> str:
    """This host's PATH, extended as search_path() describes."""
    return search_path(os.environ.get("PATH", ""), platform.system(), platform.machine())


class HostGateway:
    """System changes and downloads stay at one boundary."""

    def system(self) -> str:
        return platform.system()

    def machine(self) -> str:
        return platform.machine()

    def ubuntu_supported(self) -> bool:
        release = platform.freedesktop_os_release()
        return release.get("ID") == "ubuntu" and release.get("VERSION_ID") == "24.04"

    def run(self, command: list[str], cwd: Path | None = None) -> None:
        subprocess.run(command, cwd=cwd, check=True)

    def has_build_tools(self) -> bool:
        """A C compiler and make that work, not only their names on PATH.

        On macOS, /usr/bin/cc and /usr/bin/make exist without the Command Line Tools: they
        are stubs that offer to install them. xcode-select -p fails until they are installed.
        """
        if self.system() == "Darwin":
            try:
                found = subprocess.run(["xcode-select", "-p"], capture_output=True, check=False)
            except OSError:
                return False
            return found.returncode == 0
        return all(shutil.which(command) for command in ("cc", "make"))

    def has_command(self, name: str) -> bool:
        return shutil.which(name, path=host_path()) is not None

    def has_library(self, name: str) -> bool:
        pkg_config = shutil.which("pkg-config", path=host_path())
        if not pkg_config:
            return False
        found = subprocess.run([pkg_config, "--exists", name], check=False)
        return found.returncode == 0

    def download(self, url: str, destination: Path) -> None:
        with urllib.request.urlopen(url, timeout=60) as response:
            destination.write_bytes(response.read())

    def brew(self) -> str:
        found = shutil.which("brew")
        if found:
            return found
        for candidate in ("/opt/homebrew/bin/brew", "/usr/local/bin/brew"):
            if Path(candidate).is_file():
                return candidate
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "install.sh"
            self.download(
                "https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh", script
            )
            self.run(["env", "NONINTERACTIVE=1", "/bin/bash", str(script)])
        return "/opt/homebrew/bin/brew"

    def dependencies(self) -> None:
        prefix = [] if os.geteuid() == 0 else ["sudo", "-n"]
        self.run([*prefix, "apt-get", "update"])
        packages = [ubuntu for _, ubuntu in (*XROAR_COMMANDS.values(), *XROAR_LIBRARIES.values())]
        self.run([*prefix, "apt-get", "install", "-y", "build-essential", *packages, *XROAR_EXTRAS])


def cached_archive(
    name: str,
    version: str,
    url: str,
    checksum: str,
    root: Path,
    download: Callable[[str, Path], None],
) -> Path:
    """Return a release archive, downloading it once; its bytes must match the checksum."""
    cache = root / "local/toolchain-sources"
    cache.mkdir(parents=True, exist_ok=True)
    archive = cache / f"{name}-{version}.tar.gz"
    if not archive.exists():
        with tempfile.TemporaryDirectory(dir=cache) as directory:
            temporary = Path(directory) / "download"
            download(url, temporary)
            if hashlib.sha256(temporary.read_bytes()).hexdigest() != checksum:
                raise ValueError(f"{name}: source checksum mismatch")
            temporary.replace(archive)
    if hashlib.sha256(archive.read_bytes()).hexdigest() != checksum:
        raise ValueError(f"{name}: cached source checksum mismatch; inspect {archive}")
    return archive


def cached_source(name: str, root: Path, download: Callable[[str, Path], None]) -> Path:
    """Return the pinned release archive of a package in SOURCES."""
    return cached_archive(name, *SOURCES[name], root, download)


def build_source(name: str, root: Path, host: HostGateway) -> None:
    version = SOURCES[name][0]
    archive = cached_source(name, root, host.download)
    cache = archive.parent
    prefix = root / "local/toolchain"
    with tempfile.TemporaryDirectory(dir=cache) as directory:
        with tarfile.open(archive) as source:
            source.extractall(directory, filter="data")
        work = Path(directory) / f"{name}-{version}"
        if name == "toolshed":
            # The FUSE file system tool needs libfuse; the disk tools do not.
            work = work / "build/unix"
            host.run(["make", "NO_COCOFUSE=1"], cwd=work)
            host.run(["make", "NO_COCOFUSE=1", "install", f"prefix={prefix}"], cwd=work)
            return
        host.run(["make", "-j2"], cwd=work)
        host.run(["make", "install", f"PREFIX={prefix}"], cwd=work)


def install_toolshed(root: Path, host: HostGateway) -> bool:
    """Build ToolShed, or explain why not; only disk images need it, so it never stops setup."""
    try:
        if not host.has_build_tools():
            raise ValueError(
                "building it needs a C compiler and make. On macOS, install the Xcode "
                "Command Line Tools with xcode-select --install"
            )
        build_source("toolshed", root, host)
        if not tool_path("decb", root):
            raise ValueError("the build finished but decb is not discoverable")
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(
            f"ToolShed was not installed: {error}. Directly launched programs do not need it. "
            "Disk images do: resolve the cause, then run uv run python scripts/native.py again.",
            file=sys.stderr,
        )
        return False
    return True


def missing_tools(root: Path) -> list[str]:
    """Tools to install; an override that names an unavailable executable is an error."""
    missing = [name for name in VARIABLES if not tool_path(name, root)]
    for name in missing:
        if VARIABLES[name] in os.environ:
            raise ValueError(
                f"{VARIABLES[name]} points to an unavailable executable; correct the override."
            )
    return missing


def missing_xroar_needs(host: HostGateway) -> list[str]:
    """The commands and libraries of XROAR_COMMANDS and XROAR_LIBRARIES the host lacks."""
    commands = [name for name in XROAR_COMMANDS if not host.has_command(name)]
    return commands + [name for name in XROAR_LIBRARIES if not host.has_library(name)]


def homebrew_formulae(packages: list[str], needs: list[str]) -> list[str]:
    """Homebrew supplies LWTOOLS and the XRoar build's needs. It has no ToolShed formula."""
    supplied = {**XROAR_COMMANDS, **XROAR_LIBRARIES}
    formulae = [package for package in packages if package != "toolshed"]
    return formulae + [supplied[name][0] for name in needs]


def install_packages(root: Path, host: HostGateway, packages: list[str], needs: list[str]) -> None:
    if host.system() == "Darwin":
        if formulae := homebrew_formulae(packages, needs):
            host.run([host.brew(), "install", *formulae])
    elif host.system() == "Linux" and host.ubuntu_supported():
        host.dependencies()
        for package in packages:
            if package != "toolshed":
                build_source(package, root, host)
    else:
        raise ValueError(
            "Automatic installation supports Apple Silicon macOS and Ubuntu 24.04. "
            "See guidance/starter/toolchain.md."
        )


def install(root: Path = ROOT, host: HostGateway | None = None) -> None:
    host = host or HostGateway()
    if host.system() == "Darwin" and host.machine() != "arm64":
        raise ValueError(
            "macOS requires Apple Silicon (arm64); Intel Macs are unsupported. "
            "Use a native arm64 terminal and Python on Apple Silicon, or Ubuntu 24.04. "
            "See guidance/starter/toolchain.md."
        )
    missing = missing_tools(root)
    needs = missing_xroar_needs(host)
    if not missing and not needs:
        print("Assembly and disk tools, and what the XRoar build needs, are already available.")
        return
    packages = list(dict.fromkeys(PACKAGES[name] for name in missing))
    install_packages(root, host, packages, needs)
    if any(not tool_path(name, root) for name in missing if PACKAGES[name] != "toolshed"):
        raise ValueError(
            "Installation finished but tools are not discoverable. See guidance/starter/toolchain.md."
        )
    if still := missing_xroar_needs(host):
        raise ValueError(
            f"Installation finished but the XRoar build still lacks {', '.join(still)}. "
            "See guidance/starter/toolchain.md#instrumented-xroar."
        )
    if "toolshed" in packages:
        install_toolshed(root, host)


def main() -> int:
    try:
        install()
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"Tool installation stopped: {error}", file=sys.stderr)
        print(
            "Your agent may need your approval for system installation. Rerun after resolving it.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

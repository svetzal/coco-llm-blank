"""Install the assembly and emulator tools for Apple Silicon macOS or Ubuntu 24.04."""

import hashlib
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOMEBREW_BIN = Path("/opt/homebrew/bin")
SOURCES = {
    "lwtools": (
        "4.25",
        "https://www.lwtools.ca/releases/lwtools/lwtools-4.25.tar.gz",
        "9bb97e987d486d7abd85d04cb98a53f666f02785c108647b795c4a111c5eb09f",
    ),
    "xroar": (
        "1.12.1",
        "https://www.6809.org.uk/xroar/dl/xroar-1.12.1.tar.gz",
        "ba525225fbd732c4dbf2cbb571dc9d2810fd9dcedf0482133cf637e2eef61f88",
    ),
}


def tool_path(name: str, root: Path = ROOT) -> str | None:
    """Honor overrides, project tools, PATH, then Apple Silicon Homebrew."""
    variable = {"lwasm": "LWASM", "lwlink": "LWLINK", "xroar": "XROAR"}[name]
    if variable in os.environ:
        return shutil.which(os.environ[variable])
    local = root / "local/toolchain/bin" / name
    found = shutil.which(str(local)) or shutil.which(name)
    if found:
        return found
    if platform.system() == "Darwin" and platform.machine() == "arm64":
        return shutil.which(str(HOMEBREW_BIN / name))
    return None


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
        self.run(
            [
                *prefix,
                "apt-get",
                "install",
                "-y",
                "build-essential",
                "pkg-config",
                "libsdl2-dev",
                "libpng-dev",
                "libpulse-dev",
                "libasound2-dev",
            ]
        )


def build_source(name: str, root: Path, host: HostGateway) -> None:
    version, url, checksum = SOURCES[name]
    cache = root / "local/toolchain-sources"
    cache.mkdir(parents=True, exist_ok=True)
    archive = cache / f"{name}-{version}.tar.gz"
    if not archive.exists():
        with tempfile.TemporaryDirectory(dir=cache) as directory:
            temporary = Path(directory) / "download"
            host.download(url, temporary)
            if hashlib.sha256(temporary.read_bytes()).hexdigest() != checksum:
                raise ValueError(f"{name}: source checksum mismatch")
            temporary.replace(archive)
    if hashlib.sha256(archive.read_bytes()).hexdigest() != checksum:
        raise ValueError(f"{name}: cached source checksum mismatch; inspect {archive}")
    prefix = root / "local/toolchain"
    with tempfile.TemporaryDirectory(dir=cache) as directory:
        with tarfile.open(archive) as source:
            source.extractall(directory, filter="data")
        work = Path(directory) / f"{name}-{version}"
        if name == "xroar":
            host.run(
                [
                    "./configure",
                    f"--prefix={prefix}",
                    "--without-gtk2",
                    "--without-gtk3",
                    "--without-sdl3",
                    "--enable-ui-sdl",
                ],
                cwd=work,
            )
        host.run(["make", "-j2"], cwd=work)
        host.run(["make", "install", f"PREFIX={prefix}"], cwd=work)


def install(root: Path = ROOT, host: HostGateway | None = None) -> None:
    host = host or HostGateway()
    if host.system() == "Darwin" and host.machine() != "arm64":
        raise ValueError(
            "macOS requires Apple Silicon (arm64); Intel Macs are unsupported. "
            "Use a native arm64 terminal and Python on Apple Silicon, or Ubuntu 24.04. "
            "See guidance/toolchain.md."
        )
    missing = [name for name in ("lwasm", "lwlink", "xroar") if not tool_path(name, root)]
    if not missing:
        print("Assembly and emulator tools are already available.")
        return
    for name in missing:
        variable = {"lwasm": "LWASM", "lwlink": "LWLINK", "xroar": "XROAR"}[name]
        if variable in os.environ:
            raise ValueError(
                f"{variable} points to an unavailable executable; correct the override."
            )
    if host.system() == "Darwin":
        packages = [
            name
            for name, needed in (
                ("lwtools", any(n != "xroar" for n in missing)),
                ("xroar", "xroar" in missing),
            )
            if needed
        ]
        host.run([host.brew(), "install", *packages])
    elif host.system() == "Linux" and host.ubuntu_supported():
        host.dependencies()
        if any(name != "xroar" for name in missing):
            build_source("lwtools", root, host)
        if "xroar" in missing:
            build_source("xroar", root, host)
    else:
        raise ValueError(
            "Automatic installation supports Apple Silicon macOS and Ubuntu 24.04. See guidance/toolchain.md."
        )
    if any(not tool_path(name, root) for name in missing):
        raise ValueError(
            "Installation finished but tools are not discoverable. See guidance/toolchain.md."
        )


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

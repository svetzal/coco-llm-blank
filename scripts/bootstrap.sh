#!/bin/sh
# Prepare the host-side environment without requiring Python in advance.
set -eu

case "${1:-}" in
    coco1|coco2|coco2b|coco3) target=$1 ;;
    -h|--help)
        echo 'Usage: sh scripts/bootstrap.sh coco1|coco2|coco2b|coco3'
        echo 'Prepare Python, tools, project notes, and verified firmware for an emulator demo.'
        echo 'Missing uv is installed with Homebrew when available, otherwise its official installer.'
        exit 0 ;;
    *) echo 'Choose a machine: sh scripts/bootstrap.sh coco1|coco2|coco2b|coco3' >&2; exit 2 ;;
esac
if [ "$#" -ne 1 ]; then
    echo 'Supply exactly one machine target.' >&2
    exit 2
fi
if [ "$(uname -s)" = Darwin ] && [ "$(uname -m)" != arm64 ]; then
    echo 'macOS requires Apple Silicon (arm64); Intel Macs are unsupported. Use a native arm64 terminal on Apple Silicon, or Ubuntu 24.04. See guidance/starter/toolchain.md.' >&2
    exit 1
fi
project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$project_dir"

next_uv=uv
if ! command -v uv >/dev/null 2>&1; then
    PATH="$PATH:$HOME/.local/bin"
    export PATH
    next_uv='"$HOME/.local/bin/uv"'
fi

if ! command -v uv >/dev/null 2>&1; then
    if command -v brew >/dev/null 2>&1; then
        echo 'Installing uv with Homebrew.'
        brew install uv
        next_uv=uv
    else
        if ! command -v curl >/dev/null 2>&1; then
            if ! command -v apt-get >/dev/null 2>&1; then
                echo 'curl is missing. Install curl and CA certificates with your system package manager, then rerun bootstrap.' >&2
                exit 1
            fi
            if [ "$(id -u)" -eq 0 ]; then
                set --
            elif command -v sudo >/dev/null 2>&1; then
                set -- sudo -n
            else
                echo 'Installing curl requires root or non-interactive sudo. Ask an administrator to install curl and ca-certificates, then rerun bootstrap.' >&2
                exit 1
            fi
            echo 'Installing curl and CA certificates with apt.'
            if ! "$@" apt-get update || ! "$@" apt-get install -y curl ca-certificates; then
                echo 'Could not install curl and ca-certificates. Resolve the apt error above and ensure root or non-interactive sudo access, then rerun bootstrap.' >&2
                exit 1
            fi
        fi
        echo 'Installing uv with its official installer.'
        installer=$(mktemp)
        trap 'rm -f "$installer"' EXIT HUP INT TERM
        curl --fail --location --silent --show-error https://astral.sh/uv/install.sh -o "$installer"
        UV_INSTALL_DIR="$HOME/.local/bin" UV_NO_MODIFY_PATH=1 sh "$installer"
    fi
fi

printf 'For later commands, uv is at: %s\n' "$(command -v uv)"
echo 'Preparing the project Python environment. The first run can take a while.'
uv sync --locked
echo 'Preparing the local reference index without converting books or downloading firmware.'
uv run python scripts/setup.py --target "$target" --guidance-only
echo 'Installing missing assembly and disk tools, and what the XRoar build needs.'
uv run python scripts/native.py
echo 'Building XRoar from its pinned release. The first build takes a minute or two.'
uv run python scripts/instrumented_xroar.py build
echo 'Downloading and verifying firmware for the selected machine.'
uv run python scripts/setup.py --target "$target" --roms-only
echo 'Checking tools and firmware for a directly launched emulator demo.'
uv run python scripts/doctor.py --profile demo --target "$target"
echo 'Tools and firmware are ready. To check the first-screen example, run this from the starter folder:'
printf '%s run python scripts/coco.py check examples/first-screen --target %s\n' "$next_uv" "$target"
if [ "$next_uv" != uv ]; then
    echo 'To use the uv commands in the guides, run this once in each new terminal:'
    echo 'export PATH="$PATH:$HOME/.local/bin"'
fi

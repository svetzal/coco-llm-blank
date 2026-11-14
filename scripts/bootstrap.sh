#!/bin/sh
# Prepare the host-side environment without requiring Python in advance.
set -eu

case "${1:-}" in
    coco1|coco2|coco3) target=$1 ;;
    -h|--help)
        echo 'Usage: sh scripts/bootstrap.sh coco1|coco2|coco3'
        echo 'Prepare Python, tools, project notes, and verified firmware for an emulator demo.'
        echo 'Missing uv is installed with Homebrew when available, otherwise its official installer.'
        exit 0 ;;
    *) echo 'Choose a machine: sh scripts/bootstrap.sh coco1|coco2|coco3' >&2; exit 2 ;;
esac
if [ "$#" -ne 1 ]; then
    echo 'Supply exactly one machine target.' >&2
    exit 2
fi
project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$project_dir"

if ! command -v uv >/dev/null 2>&1; then
    if command -v brew >/dev/null 2>&1; then
        echo 'Installing uv with Homebrew.'
        brew install uv
    else
        echo 'Installing uv with its official installer.'
        installer=$(mktemp)
        trap 'rm -f "$installer"' EXIT HUP INT TERM
        curl --fail --location --silent --show-error https://astral.sh/uv/install.sh -o "$installer"
        UV_INSTALL_DIR="$HOME/.local/bin" UV_NO_MODIFY_PATH=1 sh "$installer"
        PATH="$HOME/.local/bin:$PATH"
        export PATH
    fi
fi

printf 'For later commands, uv is at: %s\n' "$(command -v uv)"
echo 'Preparing the project Python environment. The first run can take a while.'
uv sync --locked
echo 'Preparing project notes without converting books or downloading firmware.'
uv run python scripts/setup.py --target "$target" --guidance-only
echo 'Installing missing assembly and emulator tools.'
uv run python scripts/native.py
echo 'Downloading and verifying firmware for the selected machine.'
uv run python scripts/setup.py --target "$target" --roms-only
echo 'Checking tools and firmware for a directly launched emulator demo.'
uv run python scripts/doctor.py --profile demo --target "$target"
echo 'Tools and firmware are ready. Run the selected example check before its GUI launch.'

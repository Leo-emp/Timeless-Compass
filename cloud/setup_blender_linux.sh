#!/usr/bin/env bash
# Install everything a Linux cloud machine (GitHub Actions runner / Kaggle notebook) needs to render our scenes:
#   portable Blender 5.3 + the free MPFB (MakeHuman) extension + its CC0 asset pack. All free, nothing secret.
# Usage: bash cloud/setup_blender_linux.sh [install_dir]   -> prints the blender path on the last line
set -euo pipefail
DIR="${1:-$HOME/tools}"
mkdir -p "$DIR" && cd "$DIR"
if [ ! -x blender-5.3.0-linux-x64/blender ]; then
  curl -sSL -o blender.tar.xz https://download.blender.org/release/Blender5.3/blender-5.3.0-linux-x64.tar.xz
  tar -xf blender.tar.xz && rm blender.tar.xz
fi
B="$DIR/blender-5.3.0-linux-x64/blender"
"$B" -b --online-mode --command extension sync >/dev/null
"$B" -b --online-mode --command extension install --enable mpfb >/dev/null
DATA=$("$B" -b --python-expr "import bpy,os; print('MPFBDATA=' + os.path.join(bpy.utils.extension_path_user('bl_ext.blender_org.mpfb', create=True), 'data'))" 2>/dev/null | grep '^MPFBDATA=' | cut -d= -f2)
if [ ! -d "$DATA/skins" ]; then
  curl -sSL -o mh.zip https://files.makehumancommunity.org/asset_packs/makehuman_system_assets/makehuman_system_assets_cc0.zip
  mkdir -p "$DATA" && unzip -q -o mh.zip -d "$DATA" && rm mh.zip
fi
echo "$B"

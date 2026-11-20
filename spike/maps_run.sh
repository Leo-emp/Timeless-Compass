#!/bin/bash
# WS19: wait for the shared Blender lock, take it, run one Blender job, release it (also on errors).
# usage: bash spike/maps_run.sh <log> -- <blender args...>
LOG=$1; shift; shift
LOCK=spike/BLENDER_LOCK
BL="C:/Users/User/tools/blender-5.3.0-windows-x64/blender.exe"
free_gb() { powershell -NoProfile -c "[math]::Floor((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB*10)"; }
# wait: no lock, no other Blender, and at least 2.5 GB RAM free (the laptop has 16 GB and several sessions)
while [ -f "$LOCK" ] || tasklist 2>/dev/null | grep -qi "^blender.exe" || [ "$(free_gb)" -lt 25 ]; do sleep 30; done
echo "Session M (WS19 maps) $(date +%H:%M:%S) $$ $*" > "$LOCK"
trap 'rm -f "$LOCK"' EXIT
"$BL" -b "$@" > "$LOG" 2>&1
echo "EXIT $?" >> "$LOG"

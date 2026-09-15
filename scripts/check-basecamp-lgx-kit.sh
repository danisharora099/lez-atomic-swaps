#!/usr/bin/env bash
# check-basecamp-lgx-kit.sh <package.lgx>...
#
# A packaged Basecamp desk must carry the shared UI kit next to its Main.qml
# in every variant it ships; a package without it compiles nowhere (#50).
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

[[ $# -gt 0 ]] || { echo "usage: $0 <package.lgx>..." >&2; exit 64; }
kit=()
for file in apps/basecamp/common/qml/*.qml; do kit+=("$(basename "$file")"); done

status=0
for archive in "$@"; do
  entries="$(tar -tzf "$archive")"
  variants="$(printf '%s\n' "$entries" | sed -n 's|^variants/\([^/]*\)/qml/Main\.qml$|\1|p')"
  if [[ -z "$variants" ]]; then
    echo "$archive: no variant carries qml/Main.qml" >&2
    status=1
    continue
  fi
  while IFS= read -r variant; do
    missing=()
    for name in "${kit[@]}"; do
      printf '%s\n' "$entries" | grep -qx "variants/$variant/qml/$name" || missing+=("$name")
    done
    if [[ ${#missing[@]} -gt 0 ]]; then
      echo "$archive: variant $variant lacks the shared UI kit: ${missing[*]}" >&2
      status=1
    else
      echo "$archive: variant $variant carries the shared UI kit (${#kit[@]} files)"
    fi
  done <<< "$variants"
done
exit "$status"

#!/usr/bin/env bash
# Usage: bash mobile.sh DEVICE_ID APP_ID RUN_DIR [FLOW_OR_DIRECTORY ...]
set -eu
if [ "$#" -lt 3 ] || [ -z "${1:-}" ] || [ -z "${2:-}" ] || [ -z "${3:-}" ]; then
  echo "Usage : bash mobile.sh DEVICE_ID APP_ID RUN_DIR [FLOW ...]" >&2
  exit 2
fi
device=$1
app=$2
run=$3
shift 3
if [ "$#" -eq 0 ]; then
  : "${READY_ID:?Renseigner l’identifiant accessible de l’écran attendu}"
  set -- "$(dirname "$0")/../assets/maestro"
fi
command -v maestro >/dev/null || { echo "Maestro CLI est requis." >&2; exit 2; }
umask 077
mkdir -p "$(dirname "$run")"
mkdir "$run" || { echo "Choisir un nouveau dossier pour cette exécution." >&2; exit 2; }
maestro --version > "$run/maestro-version.txt"
printf '%s\n' "$device" "$app" > "$run/target.txt"
status=0
maestro --device "$device" test -e "APP_ID=$app" -e "READY_ID=${READY_ID:-}" \
  --format JUNIT --output "$run/junit.xml" --test-output-dir "$run/artifacts" \
  "$@" || status=$?
printf '%s\n' "$status" > "$run/exit-code.txt"
exit "$status"

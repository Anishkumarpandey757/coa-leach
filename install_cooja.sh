#!/bin/sh
set -eu
if [ "$#" -ne 1 ]; then
  echo "Usage: sh install_cooja.sh /absolute/path/to/contiki-ng" >&2
  exit 1
fi
REPO=$(cd "$1" && pwd)
ROOT=$(cd "$(dirname "$0")" && pwd)
if [ ! -f "$REPO/Makefile.include" ] || [ ! -f "$REPO/examples/rpl-udp/rpl-udp-cooja.csc" ]; then
  echo "Error: cannot find valid Contiki-NG repo or upstream Cooja example at $REPO" >&2
  exit 1
fi
mkdir -p "$REPO/examples/coa-apso-leach"
cp "$ROOT"/cooja/*.c "$ROOT"/cooja/*.h "$ROOT"/cooja/Makefile "$REPO/examples/coa-apso-leach/"
python3 "$ROOT/make_cooja_scenario.py" "$REPO"
echo "Installed Contiki-NG example in $REPO/examples/coa-apso-leach"
echo "Next: cd '$REPO/tools/cooja' && ./gradlew run"

#!/bin/sh
set -eu
CONTIKI_REPO="${CONTIKI_REPO:-$HOME/coa-demo/contiki-ng}"
cd "$CONTIKI_REPO/tools/cooja"
exec java -jar build/libs/cooja.jar --contiki="$CONTIKI_REPO" \
  "$CONTIKI_REPO/examples/coa-apso-leach/demo.csc"

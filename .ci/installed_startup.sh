#!/bin/bash

set -euo pipefail

VENV=${1:?usage: $0 VENV}
PYTHON="$VENV/bin/python"
GALAXY="$VENV/bin/galaxy"
URL=http://localhost:8080
TRIES=120
WORK_DIR=$(mktemp -d -t galaxy-installed-startupXXXXXX)
LOG_FILE="$WORK_DIR/galaxy.log"
GALAXY_PID=
STOP_TIMEOUT=30

# Galaxy runs in its own process group, whose id is GALAXY_PID.
galaxy_stopped_within() {
    for ((i = 0; i < $1; i++)); do
        kill -0 -- "-$GALAXY_PID" 2>/dev/null || return 0
        sleep 1
    done
    return 1
}

# Signal the whole group: the gravity launcher does not pass SIGTERM on to the
# gunicorn and celery processes it starts, and those write under WORK_DIR.
stop_galaxy() {
    kill -TERM -- "-$GALAXY_PID" 2>/dev/null || return 0
    if ! galaxy_stopped_within "$STOP_TIMEOUT" 2>/dev/null; then
        echo "Galaxy processes still running $STOP_TIMEOUT seconds after SIGTERM; sending SIGKILL." >&2
        kill -KILL -- "-$GALAXY_PID" 2>/dev/null || true
        galaxy_stopped_within 10 2>/dev/null || true
    fi
    wait "$GALAXY_PID" 2>/dev/null || true
}

cleanup() {
    exit_code=$?
    if [ -n "$GALAXY_PID" ]; then
        stop_galaxy
    fi
    if [ "$exit_code" -ne 0 ] && [ -f "$LOG_FILE" ]; then
        echo "Installed Galaxy startup failed; showing $LOG_FILE:"
        cat "$LOG_FILE"
    fi
    rm -rf "$WORK_DIR"
    exit "$exit_code"
}
trap cleanup EXIT

"$PYTHON" - <<'PY'
import sys
from pathlib import Path

import galaxy.web_client

package_path = Path(galaxy.web_client.__file__).resolve()
venv_path = Path(sys.prefix).resolve()
if not package_path.is_relative_to(venv_path):
    raise SystemExit(f"galaxy.web_client resolved outside the installed environment: {package_path}")
PY

ASSET=$(
    "$PYTHON" - <<'PY'
from importlib.resources import files

dist = files("galaxy.web_client").joinpath("dist")
print(next(asset.name for asset in dist.iterdir() if asset.name.startswith("galaxy-app-") and asset.name.endswith(".js")))
PY
)

cd "$WORK_DIR"
export GALAXY_CONFIG_DATABASE_AUTO_MIGRATE=true
export PATH="$VENV/bin:$PATH"
# Job control starts the background job in a new process group.
set -m
"$GALAXY" >"$LOG_FILE" 2>&1 &
GALAXY_PID=$!
set +m

for ((i = 0; i <= TRIES; i++)); do
    if curl --fail --max-time 1 --silent --output /dev/null "$URL/api/version"; then
        curl --fail --max-time 5 --silent --output /dev/null "$URL/"
        curl --fail --max-time 5 --silent --output /dev/null "$URL/static/dist/$ASSET"
        exit 0
    fi
    if ! kill -0 "$GALAXY_PID" 2>/dev/null; then
        echo "Installed Galaxy exited before becoming ready." >&2
        exit 1
    fi
    sleep 1
done

echo "Installed Galaxy did not become ready after $TRIES seconds." >&2
exit 1

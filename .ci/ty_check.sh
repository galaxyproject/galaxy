#!/bin/bash
# Keep a stable entry point for make, package checks, and exemption pruning.
set -euo pipefail
exec python "$(dirname "${BASH_SOURCE[0]}")/ty_check.py" "$@"

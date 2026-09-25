#!/usr/bin/env sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repo_root=$(CDPATH= cd -- "$script_dir/.." && pwd)
cd "$repo_root"

printf 'EnvBisect: 46 differences, one two-variable interaction\n'
sleep 2
envbisect diagnose \
  --pass examples/demo/pass.env \
  --fail examples/demo/fail.env \
  -- python examples/demo/app.py
printf '\nResult: FEATURE_CACHE and TZ act together in this demo.\n'
sleep 12

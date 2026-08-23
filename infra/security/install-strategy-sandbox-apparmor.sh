#!/usr/bin/env bash
set -euo pipefail

profile_path="$(cd "$(dirname "$0")" && pwd)/strategy-sandbox.apparmor"

if [[ "$(uname -s)" != "Linux" ]] || ! command -v apparmor_parser >/dev/null 2>&1; then
  echo "AppArmor is unavailable; leave CSL_STRATEGY_SANDBOX_APPARMOR_PROFILE unset." >&2
  exit 1
fi

apparmor_parser --replace "$profile_path"
echo "Installed crypto-lab-strategy-sandbox. Set CSL_STRATEGY_SANDBOX_APPARMOR_PROFILE=crypto-lab-strategy-sandbox."

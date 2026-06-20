#!/usr/bin/env bash
set -Eeuo pipefail

WORKDIR="/Users/wangwenhui/Documents/keiko_stock"
cd "$WORKDIR"

mkdir -p logs

RUN_LOG="logs/iwencai_profile_slow_resume_$(date '+%Y%m%d_%H%M%S').log"
PID_FILE="logs/iwencai_profile_slow_resume.pid"
LOCK_DIR="logs/iwencai_profile_slow_resume.lock"

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  echo "$(date '+%Y-%m-%d %H:%M:%S') another iwencai slow resume job is already running; lock=$LOCK_DIR"
  exit 0
fi

cleanup() {
  rm -rf "$LOCK_DIR"
  rm -f "$PID_FILE"
}
trap cleanup EXIT

echo "$$" > "$PID_FILE"

{
  echo "started_at=$(date '+%Y-%m-%d %H:%M:%S %Z %z')"
  echo "workdir=$WORKDIR"
  echo "pid=$$"
  echo "mode=slow_resume"
  echo "policy=skip ok/no_sections fresher than 168h; crawl failed and uncrawled targets"
  echo "circuit=5 consecutive 403 -> pause 7200s -> new session/token -> continue"
  echo
} >> "$RUN_LOG"

set +e
python3 -u scripts/crawl_iwencai_profile.py \
  --tier all \
  --stale-hours 168 \
  --sleep 8 \
  --jitter 7 \
  --timeout 30 \
  --max-retries 1 \
  --circuit-403-threshold 5 \
  --circuit-cooldown-seconds 7200 \
  --status-every 25 \
  >> "$RUN_LOG" 2>&1
exit_code=$?
set -e

{
  echo
  echo "finished_at=$(date '+%Y-%m-%d %H:%M:%S %Z %z')"
  echo "exit_code=$exit_code"
} >> "$RUN_LOG"

exit "$exit_code"

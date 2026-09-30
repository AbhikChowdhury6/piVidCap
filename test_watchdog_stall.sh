#!/bin/bash
# Exercises watchdog.sh against real tmux sessions rather than mocks, using a
# stand-in for main.py that can reproduce each way piVidCap has been seen to
# stop capturing:
#   SIGUSR1 -- hard hang: process alive, no output at all
#   SIGUSR2 -- camera gone: still logging every tick, frame counter frozen
#              (writerWorker's `output is None` retry path; the failure that
#              went unalerted for 27h on 2026-09-28)
set -uo pipefail

WD="$(cd "$(dirname "$0")" && pwd)/watchdog.sh"
TMP="$(mktemp -d)"
SESSION="wdtest-$$"
FAKE_REPO="$TMP/repo"
PASS=0
FAIL=0

cleanup() {
    tmux kill-session -t "$SESSION" 2>/dev/null
    pkill -f "$TMP/envs/vision/bin/python" 2>/dev/null
    pkill -f "python main.py writer_worker" 2>/dev/null
    rm -f "$FAKE_REPO/pinned_frames" "$FAKE_REPO/camera_gone" 2>/dev/null
    rm -rf "$TMP"
}
trap cleanup EXIT

check() {
    local label="$1" expected="$2" actual="$3"
    if [ "$expected" = "$actual" ]; then
        echo "  PASS  $label"
        PASS=$(( PASS + 1 ))
    else
        echo "  FAIL  $label"
        echo "          expected: $expected"
        echo "          actual:   $actual"
        FAIL=$(( FAIL + 1 ))
    fi
}

mkdir -p "$FAKE_REPO" "$TMP/envs/vision/bin" "$TMP/alerts"
echo "placeholder" > "$FAKE_REPO/main.py"

cat > "$TMP/envs/vision/bin/python" <<'PY'
#!/bin/bash
# Spawns a detached worker in its own session, so it survives tmux tearing
# down the pane -- the orphan-holding-the-camera shape the watchdog must
# clean up before a replacement can capture.
setsid bash -c 'exec -a "python main.py writer_worker" sleep 600' </dev/null >/dev/null 2>&1 &
mode=running
# A camera that is still unplugged means every restart comes up broken too.
[ -f ./camera_gone ] && mode=nocamera
frames=0
# When ./pinned_frames exists its contents are reported verbatim as the frame
# count, letting a test reproduce a coarse counter that reads the same on two
# consecutive samples while the pipeline is in fact alive.
pinned() { [ -f ./pinned_frames ] && cat ./pinned_frames; }
trap 'mode=hung' USR1
trap 'mode=nocamera' USR2
while true; do
    case "$mode" in
        running)
            frames=$(( frames + 1 ))
            echo "writer: model result is 0"
            echo "writer: have $(pinned || echo $frames) frames in the current video"
            ;;
        nocamera)
            echo "writer: model result is 0"
            echo "writer: no open video writer, skipping this tick's frames and will retry"
            echo "writer: have $frames frames in the current video"
            ;;
        hung) : ;;
    esac
    sleep 1 &
    wait $!
done
PY
chmod +x "$TMP/envs/vision/bin/python"

run_wd() {
    env SESSION="$SESSION" WINDOW=pividcap REPO_DIR="$FAKE_REPO" \
        STATE_DOWN_SINCE="$TMP/down_since" STATE_ALERT_SENT="$TMP/alert_sent" \
        STATE_PROGRESS="$TMP/progress" WATCHER_LOG="$TMP/watcher.log" \
        PYTHON_ENV_ROOT="$TMP/envs" ALERT_DEST="$TMP/alerts" \
        HOSTNAME_SHORT="testnode" \
        STALL_THRESHOLD_SECONDS="${STALL_THRESHOLD:-3}" \
        STALL_CONFIRM_SECONDS="${STALL_CONFIRM:-1}" \
        ALERT_THRESHOLD_SECONDS="${ALERT_THRESHOLD:-6}" \
        bash "$WD"
}

start_session() {
    tmux kill-session -t "$SESSION" 2>/dev/null
    tmux new-session -d -s "$SESSION" -n pividcap \
        "cd $FAKE_REPO && exec $TMP/envs/vision/bin/python main.py"
    sleep 2
}

fake_pid() {
    local pid
    for pid in $(pgrep -f "$TMP/envs/vision/bin/python" 2>/dev/null); do
        if [ "$(readlink "/proc/$pid/cwd" 2>/dev/null)" = "$FAKE_REPO" ]; then
            echo "$pid"; return
        fi
    done
}

reset_state() { rm -f "$TMP/down_since" "$TMP/alert_sent" "$TMP/progress"; }

echo "TEST 1: healthy capture is left alone"
start_session
run_wd; sleep 1; run_wd
check "no down-since recorded"    "absent" "$([ -f "$TMP/down_since" ] && echo present || echo absent)"
check "no alert marker"           "0"      "$(ls -1 "$TMP/alerts" | wc -l)"
pid_before="$(fake_pid)"
check "capture process untouched" "alive"  "$([ -n "$pid_before" ] && echo alive || echo gone)"

echo
echo "TEST 2: hard hang (no output) is detected and restarted"
kill -USR1 "$pid_before"; sleep 1
run_wd
check "grace period, not yet stalled" "absent" "$([ -f "$TMP/down_since" ] && echo present || echo absent)"
sleep 4
run_wd
check "down-since recorded"         "present" "$([ -f "$TMP/down_since" ] && echo present || echo absent)"
check "no-frames reason logged"     "1" "$(grep -c 'window alive but no frames written' "$TMP/watcher.log")"
check "orphan reaped"               "1" "$(grep -c 'killed 1 orphaned main.py' "$TMP/watcher.log")"
sleep 2
pid_after="$(fake_pid)"
check "new capture process up"      "new" "$([ -n "$pid_after" ] && [ "$pid_after" != "$pid_before" ] && echo new || echo "stale:${pid_after:-none}")"
check "window survived the restart" "1" "$(tmux list-windows -t "$SESSION" -F '#{window_name}' 2>/dev/null | grep -cx pividcap)"

echo
echo "TEST 3: recovery clears the outage state"
# One run re-baselines the restarted counter; the next sees it advance.
sleep 1; run_wd; sleep 1; run_wd
check "down-since cleared" "absent" "$([ -f "$TMP/down_since" ] && echo present || echo absent)"
check "recovery logged"    "1"      "$(grep -c 'capturing again' "$TMP/watcher.log")"

echo
echo "TEST 4: THE REGRESSION -- logging every tick but writing no frames"
start_session; reset_state; rm -f "$TMP/alerts"/*
: > "$TMP/watcher.log"
pid_before="$(fake_pid)"
run_wd; sleep 1
touch "$FAKE_REPO/camera_gone"    # every restart from here comes up broken
kill -USR2 "$pid_before"          # camera gone: keeps logging, counter frozen
sleep 1
run_wd
check "chatter alone is not recovery" "0" "$(grep -c 'capturing again' "$TMP/watcher.log")"
sleep 4
run_wd
check "detected despite live output"  "1" "$(grep -c 'window alive but no frames written' "$TMP/watcher.log")"
check "down-since recorded"           "present" "$([ -f "$TMP/down_since" ] && echo present || echo absent)"

echo
echo "TEST 5: an unfixable outage alerts exactly once"
# Hold every replacement in the no-camera state, as a physically unplugged
# camera would: the outage must stay open and must not re-alert per cycle.
for _ in 1 2 3 4 5 6; do
    sleep 3
    run_wd
done
marker="$(ls -1 "$TMP/alerts" 2>/dev/null | head -1)"
check "exactly one marker delivered"  "1" "$(ls -1 "$TMP/alerts" | wc -l)"
check "marker filename unprefixed"    "yes" "$(case "$marker" in airqualpi_*) echo no;; testnode_*.txt) echo yes;; *) echo "no:${marker:-none}";; esac)"
check "marker names the host"         "1" "$(grep -c 'testnode' "$TMP/alerts/$marker" 2>/dev/null)"
check "alert sent once only"          "1" "$(grep -c 'sent alert marker' "$TMP/watcher.log")"

echo
echo "TEST 6: window-missing path still works"
start_session; reset_state; rm -f "$TMP/alerts"/*
: > "$TMP/watcher.log"
# Add a second window first: killing a session's only window destroys the
# session, which is a different case (TEST 7).
tmux new-window -d -t "$SESSION" -n placeholder "sleep 300"
tmux kill-window -t "$SESSION:pividcap" 2>/dev/null
pkill -f "$TMP/envs/vision/bin/python" 2>/dev/null
sleep 1
run_wd
check "window-missing logged" "1" "$(grep -c 'window missing, restarting' "$TMP/watcher.log")"
check "down-since recorded"   "present" "$([ -f "$TMP/down_since" ] && echo present || echo absent)"
sleep 2
check "window recreated"      "1" "$(tmux list-windows -t "$SESSION" -F '#{window_name}' 2>/dev/null | grep -cx pividcap)"

echo
echo "TEST 7: a missing session is reported, not silently retried"
tmux kill-session -t "$SESSION" 2>/dev/null
run_wd; rc=$?
check "exits non-zero"             "1" "$rc"
check "manual-intervention logged" "yes" "$([ "$(grep -c "tmux session '$SESSION' itself is missing" "$TMP/watcher.log")" -ge 1 ] && echo yes || echo no)"

echo
echo "TEST 8: a repeated counter that moves during confirmation is not a stall"
rm -f "$FAKE_REPO/camera_gone" "$FAKE_REPO/pinned_frames"
echo 150 > "$FAKE_REPO/pinned_frames"      # counter reads the same every sample
start_session; reset_state; rm -f "$TMP/alerts"/*
: > "$TMP/watcher.log"
run_wd; sleep 4                            # baseline, then exceed the 3s threshold
( sleep 2; echo 300 > "$FAKE_REPO/pinned_frames" ) &   # moves inside the 6s confirm
STALL_CONFIRM=6 run_wd
check "no stall declared"        "0" "$(grep -c 'window alive but no frames written' "$TMP/watcher.log")"
check "non-confirmation logged"  "1" "$(grep -c 'suspected stall not confirmed' "$TMP/watcher.log")"
check "capture left running"     "absent" "$([ -f "$TMP/down_since" ] && echo present || echo absent)"
check "no alert marker"          "0" "$(ls -1 "$TMP/alerts" | wc -l)"

echo
echo "TEST 9: a genuinely frozen counter still confirms as a stall"
rm -f "$FAKE_REPO/camera_gone"
echo 500 > "$FAKE_REPO/pinned_frames"      # and nothing will move it
start_session; reset_state; rm -f "$TMP/alerts"/*
: > "$TMP/watcher.log"
run_wd; sleep 4
STALL_CONFIRM=6 run_wd
check "stall confirmed"      "1" "$(grep -c 'window alive but no frames written' "$TMP/watcher.log")"
check "down-since recorded"  "present" "$([ -f "$TMP/down_since" ] && echo present || echo absent)"

echo
echo "=============================="
echo "  passed: $PASS   failed: $FAIL"
echo "=============================="
[ "$FAIL" -eq 0 ]

#!/bin/bash
set -euo pipefail

# Restarts piVidCap when it stops capturing, and drops an alert marker on the
# upload host once an outage is sustained.
#
# Three failure modes are covered, in increasing order of subtlety:
#   1. The pividcap tmux window is gone -- main.py exited and took its window
#      with it (tmux's default when a pane's command ends).
#   2. The window is there but the process has hard-hung: no output at all.
#   3. The window is there and the process is happily logging, but no frames
#      are reaching the video file. This is what a disconnected camera looks
#      like: writerWorker's `output is None` branch prints "no open video
#      writer ... will retry" every tick forever. A liveness check based on
#      the window existing -- or even on the pane producing output -- sees a
#      perfectly healthy service. On 2026-09-28 this cost 27h of silent
#      kitchen downtime with zero alerts.
#
# The primary signal is therefore piVidCap's own frame counter, "writer: have
# N frames in the current video", which it prints every tick and which only
# advances when frames actually land in the file. Whole-pane output is the
# fallback for when no counter line is on screen (e.g. during startup).
#
# Every knob is env-overridable so the test harness can drive this script
# against a throwaway tmux session without touching a live capture.

SESSION="${SESSION:-sensors}"
WINDOW="${WINDOW:-pividcap}"
REPO_DIR="${REPO_DIR:-/home/pi/Documents/piVidCap}"
STATE_DOWN_SINCE="${STATE_DOWN_SINCE:-/home/pi/.pividcap_down_since}"
STATE_ALERT_SENT="${STATE_ALERT_SENT:-/home/pi/.pividcap_alert_sent}"
STATE_PROGRESS="${STATE_PROGRESS:-/home/pi/.pividcap_progress}"
WATCHER_LOG="${WATCHER_LOG:-/home/pi/pividcap_watcher.log}"
ALERT_THRESHOLD_SECONDS="${ALERT_THRESHOLD_SECONDS:-1800}"
# The writer loop ticks about every 15s, so a progress token that has not
# moved for this long means it has stopped doing work. Kept far above one tick
# so a slow model pass or a transient stutter can never trip it.
STALL_THRESHOLD_SECONDS="${STALL_THRESHOLD_SECONDS:-600}"
# Before acting on a suspected stall, re-sample after this long. Must comfortably
# exceed one writer tick (~15s) plus the one tick the loop legitimately skips
# right after activity ends, so a healthy pipeline always moves inside it.
STALL_CONFIRM_SECONDS="${STALL_CONFIRM_SECONDS:-45}"
UPLOAD_HOST="${UPLOAD_HOST:-uploadingGuest@192.168.20.64}"
ALERT_DIR="${ALERT_DIR:-/home/uploadingGuest/pividcap_alerts}"
# Full scp destination, overridable as one unit so the test harness can point
# it at a local directory and still exercise the real delivery path.
ALERT_DEST="${ALERT_DEST:-${UPLOAD_HOST}:${ALERT_DIR}}"
PYTHON_ENV_ROOT="${PYTHON_ENV_ROOT:-/home/pi/miniforge3/envs}"

hostname_short="${HOSTNAME_SHORT:-$(hostname)}"

log() {
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $1" >> "$WATCHER_LOG"
}

now_iso() {
    date -u +%Y-%m-%dT%H:%M:%SZ
}

resolve_env_python() {
    local env_dir
    env_dir=$(find "$PYTHON_ENV_ROOT" -mindepth 1 -maxdepth 1 -type d | sort | head -1)
    echo "${env_dir}/bin/python"
}

window_present() {
    tmux list-windows -t "$SESSION" -F '#{window_name}' 2>/dev/null | grep -qx "$WINDOW"
}

# A token summarising "what piVidCap has achieved so far". Two forms:
#   frames:<N>  -- the frame counter, proof that frames are reaching the file
#   output:<hash> -- fallback when no counter line is visible; proves only
#                    that the process is alive and printing
# A changed frames: token means genuinely capturing. A changed output: token
# means alive but unproven, which is deliberately not enough to clear an
# outage: a camera-less piVidCap logs retries forever.
progress_token() {
    local pane frames
    pane="$(tmux capture-pane -p -t "${SESSION}:${WINDOW}" 2>/dev/null || true)"
    if [ -z "$pane" ]; then
        echo "none"
        return
    fi
    frames="$(printf '%s\n' "$pane" \
        | grep -oE 'have [0-9]+ frames in the current video' \
        | tail -1 | grep -oE '[0-9]+' || true)"
    if [ -n "$frames" ]; then
        echo "frames:${frames}"
    else
        echo "output:$(printf '%s' "$pane" | md5sum | cut -d' ' -f1)"
    fi
}

# Echoes one of:
#   capturing          -- frames are demonstrably being written
#   unproven           -- alive and printing, but no frame progress observed
#   stalled <iso8601>  -- nothing has moved since that time
# Maintains STATE_PROGRESS, which holds "<token> <iso8601 first seen>".
classify_progress() {
    local token prev_token prev_since since_epoch now_epoch unchanged_for

    token="$(progress_token)"
    prev_token=""
    prev_since=""
    if [ -f "$STATE_PROGRESS" ]; then
        read -r prev_token prev_since < "$STATE_PROGRESS" || true
    fi

    if [ "$token" != "$prev_token" ]; then
        echo "$token $(now_iso)" > "$STATE_PROGRESS"
        # Only a frame count that moved *between two observations* proves
        # capture. A first sighting is a baseline: right after a restart the
        # counter reads frames:0, and a still-broken camera never leaves it.
        case "$prev_token,$token" in
            frames:*,frames:*) echo "capturing" ;;
            *)                 echo "unproven" ;;
        esac
        return
    fi

    since_epoch=$(date -u -d "$prev_since" +%s 2>/dev/null || echo 0)
    now_epoch=$(date -u +%s)
    unchanged_for=$(( now_epoch - since_epoch ))

    if [ "$since_epoch" -eq 0 ] || [ "$unchanged_for" -lt "$STALL_THRESHOLD_SECONDS" ]; then
        echo "unproven"
        return
    fi

    # Suspected stall. Confirm with a second sample in this same run rather
    # than trusting the cross-run comparison: the counter is coarse and cyclic,
    # so repeated readings are not by themselves proof that nothing moved.
    sleep "$STALL_CONFIRM_SECONDS"
    local recheck
    recheck="$(progress_token)"
    if [ "$recheck" != "$token" ]; then
        echo "$recheck $(now_iso)" > "$STATE_PROGRESS"
        log "suspected stall not confirmed ($token -> $recheck in ${STALL_CONFIRM_SECONDS}s), capture is live"
        case "$recheck" in
            frames:*) echo "capturing" ;;
            *)        echo "unproven" ;;
        esac
        return
    fi

    echo "stalled $prev_since"
}

# Restarts the capture process.
#
# When the window is still present (the stall case) the pane is respawned in
# place rather than killed: pividcap can be the session's last window, and
# killing it destroys the session -- which this script explicitly cannot
# recreate, turning a recoverable stall into manual-only downtime.
restart_capture() {
    local python_bin stale_pids pid cwd killed
    python_bin="$(resolve_env_python)"

    if ! window_present; then
        if tmux new-window -d -t "$SESSION" -n "$WINDOW" "cd $REPO_DIR && exec $python_bin main.py"; then
            log "restarted pividcap using $python_bin"
        else
            log "ERROR: tmux new-window failed to restart pividcap using $python_bin"
        fi
        return
    fi

    # Snapshot the stale process set before respawning: afterwards the fresh
    # copy is indistinguishable from an orphan by cwd alone.
    stale_pids=""
    for pid in $(pgrep -f 'main\.py' 2>/dev/null || true); do
        cwd="$(readlink "/proc/${pid}/cwd" 2>/dev/null || true)"
        if [ "$cwd" = "$REPO_DIR" ]; then
            stale_pids="$stale_pids $pid"
        fi
    done

    # Park the window on a placeholder: tmux tears down the stalled pane
    # command while the window, and so the session, stays alive.
    tmux respawn-window -k -t "${SESSION}:${WINDOW}" "sleep 30" 2>>"$WATCHER_LOG" || true

    # main.py's multiprocessing children can outlive the pane and keep holding
    # the camera, which would stop the replacement from ever capturing.
    killed=0
    for pid in $stale_pids; do
        if kill -0 "$pid" 2>/dev/null; then
            kill -TERM "$pid" 2>/dev/null || true
            killed=$(( killed + 1 ))
        fi
    done
    if [ "$killed" -gt 0 ]; then
        sleep 5
        for pid in $stale_pids; do
            kill -KILL "$pid" 2>/dev/null || true
        done
        log "killed ${killed} orphaned main.py process(es) under ${REPO_DIR}"
    fi

    if tmux respawn-window -k -t "${SESSION}:${WINDOW}" "cd $REPO_DIR && exec $python_bin main.py"; then
        log "restarted pividcap using $python_bin"
    else
        log "ERROR: tmux respawn-window failed to restart pividcap using $python_bin"
    fi
}

send_alert_if_sustained() {
    local reason="$1" down_since down_since_epoch now_epoch down_seconds marker_name marker_path
    [ -f "$STATE_DOWN_SINCE" ] || return 0
    down_since="$(cat "$STATE_DOWN_SINCE")"
    down_since_epoch=$(date -u -d "$down_since" +%s)
    now_epoch=$(date -u +%s)
    down_seconds=$(( now_epoch - down_since_epoch ))

    if [ "$down_seconds" -lt "$ALERT_THRESHOLD_SECONDS" ] || [ -f "$STATE_ALERT_SENT" ]; then
        return 0
    fi

    # Filename stays "<hostname>_<down-since>.txt": the unprefixed form is how
    # the monitor on the upload host tells piVidCap markers from airQualPi's.
    marker_name="${hostname_short}_${down_since}.txt"
    marker_path="/tmp/${marker_name}"
    echo "pividcap ${reason} since ${down_since} on ${hostname_short} (${down_seconds}s)" > "$marker_path"
    if scp -o BatchMode=yes -o ConnectTimeout=5 "$marker_path" "${ALERT_DEST}/${marker_name}" 2>>"$WATCHER_LOG"; then
        touch "$STATE_ALERT_SENT"
        log "sent alert marker (${reason}) for outage since ${down_since}"
    else
        log "failed to send alert marker (${reason}) for outage since ${down_since}"
    fi
    rm -f "$marker_path"
}

if ! tmux has-session -t "$SESSION" 2>/dev/null; then
    log "ERROR: tmux session '$SESSION' itself is missing -- cannot recover automatically, needs manual intervention"
    exit 1
fi

if window_present; then
    progress="$(classify_progress)"
else
    progress="window-missing"
fi

case "$progress" in
    capturing)
        if [ -f "$STATE_DOWN_SINCE" ]; then
            rm -f "$STATE_DOWN_SINCE" "$STATE_ALERT_SENT"
            log "pividcap capturing again, cleared down-since state"
        fi
        exit 0
        ;;
    unproven)
        # Alive and printing but with no proof of frames. Never enough on its
        # own to declare recovery -- hold any open outage, and keep alerting
        # on it if it is already sustained.
        send_alert_if_sustained "not capturing"
        exit 0
        ;;
    window-missing)
        reason="down"
        [ -f "$STATE_DOWN_SINCE" ] || now_iso > "$STATE_DOWN_SINCE"
        log "pividcap window missing, restarting"
        ;;
    stalled\ *)
        reason="stalled (window alive, no frames written)"
        # Date the outage from when progress actually stopped, not from now.
        [ -f "$STATE_DOWN_SINCE" ] || echo "${progress#stalled }" > "$STATE_DOWN_SINCE"
        log "pividcap ${progress} -- window alive but no frames written, restarting"
        ;;
esac

restart_capture
# The replacement starts from a blank counter; drop the stale token so the
# next run measures the new process instead of re-tripping on the old one.
rm -f "$STATE_PROGRESS"

send_alert_if_sustained "$reason"

#!/bin/bash
set -euo pipefail

SESSION="sensors"
WINDOW="pividcap"
REPO_DIR="/home/pi/Documents/piVidCap"
STATE_DOWN_SINCE="/home/pi/.pividcap_down_since"
STATE_ALERT_SENT="/home/pi/.pividcap_alert_sent"
WATCHER_LOG="/home/pi/pividcap_watcher.log"
ALERT_THRESHOLD_SECONDS="${ALERT_THRESHOLD_SECONDS:-1800}"
UPLOAD_HOST="uploadingGuest@192.168.20.64"
ALERT_DIR="/home/uploadingGuest/pividcap_alerts"

hostname_short="$(hostname)"

log() {
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $1" >> "$WATCHER_LOG"
}

resolve_env_python() {
    local env_dir
    env_dir=$(find /home/pi/miniforge3/envs -mindepth 1 -maxdepth 1 -type d | sort | head -1)
    echo "${env_dir}/bin/python"
}

window_present() {
    tmux list-windows -t "$SESSION" -F '#{window_name}' 2>/dev/null | grep -qx "$WINDOW"
}

if ! tmux has-session -t "$SESSION" 2>/dev/null; then
    log "ERROR: tmux session '$SESSION' itself is missing -- cannot recover automatically, needs manual intervention"
    exit 1
fi

if window_present; then
    if [ -f "$STATE_DOWN_SINCE" ]; then
        rm -f "$STATE_DOWN_SINCE" "$STATE_ALERT_SENT"
        log "pividcap window present again, cleared down-since state"
    fi
    exit 0
fi

if [ ! -f "$STATE_DOWN_SINCE" ]; then
    date -u +%Y-%m-%dT%H:%M:%SZ > "$STATE_DOWN_SINCE"
fi

python_bin="$(resolve_env_python)"
tmux new-window -t "$SESSION" -n "$WINDOW" "cd $REPO_DIR && exec $python_bin main.py"
log "pividcap window missing, restarted using $python_bin"

down_since="$(cat "$STATE_DOWN_SINCE")"
down_since_epoch=$(date -u -d "$down_since" +%s)
now_epoch=$(date -u +%s)
down_seconds=$(( now_epoch - down_since_epoch ))

if [ "$down_seconds" -ge "$ALERT_THRESHOLD_SECONDS" ] && [ ! -f "$STATE_ALERT_SENT" ]; then
    marker_name="${hostname_short}_${down_since}.txt"
    marker_path="/tmp/${marker_name}"
    echo "pividcap down since ${down_since} on ${hostname_short} (${down_seconds}s)" > "$marker_path"
    if scp -o BatchMode=yes -o ConnectTimeout=5 "$marker_path" "${UPLOAD_HOST}:${ALERT_DIR}/${marker_name}" 2>>"$WATCHER_LOG"; then
        touch "$STATE_ALERT_SENT"
        log "sent alert marker for outage since ${down_since}"
    else
        log "failed to send alert marker for outage since ${down_since}"
    fi
    rm -f "$marker_path"
fi

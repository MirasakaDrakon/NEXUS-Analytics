#!/data/data/com.termux/files/usr/bin/bash

SESSION="iplog"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ -z "$TMUX" ]; then
    tmux has-session -t "$SESSION" 2>/dev/null

    if [ $? != 0 ]; then
        # ── верхняя панель: cloudflared
        tmux new-session -d -s "$SESSION" -n main \
        "cloudflared tunnel --url http://0.0.0.0:3333; exec bash"

        # ── нижняя панель: iplogger.py
        tmux split-window -v -t "$SESSION" \
        "cd \"$SCRIPT_DIR\" && python3 iplogger.py; exec bash"

        # ── разделяем нижнюю панель на левую/правую
        tmux split-window -h -t "$SESSION":0.1 \
        "cd \"$SCRIPT_DIR\" && python3 stats2.py; exec bash"

        # ── ещё один сплит вниз под stats2.py → ipscan.py
        tmux split-window -v -t "$SESSION":0.2 \
        "cd \"$SCRIPT_DIR\" && python3 ipscan.py; exec bash"

        # фокус на верх
        tmux select-pane -t 0
    fi

    tmux attach -t "$SESSION"
else
    echo "Ты уже в tmux"
fi
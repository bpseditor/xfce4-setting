# xfce4-setting

XFCE profile for Void Linux/X11: GTK/Qt colors, panel, fonts, keyboard shortcuts, System & Power, Activity Tracker and a break reminder.

Run from your XFCE session:

```sh
curl -fsSL https://raw.githubusercontent.com/bpseditor/xfce4-setting/main/bootstrap.sh | sh
```

The bootstrap downloads this repository; `install.sh` installs packages with xbps/sudo, then applies allowlisted settings. `--power skip` skips the ThinkPad T495s power profile. That profile uses TLP with fixed 79/80% battery thresholds and disables the former charge-guard service. Other hardware receives desktop settings only.

Sources:
- GTK/XFWM base: [Bukutsu/tokyonight-xfce](https://github.com/Bukutsu/tokyonight-xfce), pinned in `install.py`; recolored by `theme.py` using an Ayu-inspired palette. Upstream license files are retained.
- Inter and JetBrains Mono: [google/fonts](https://github.com/google/fonts), pinned in `install.py`, with OFL licenses. Papirus and other dependencies come from Void packages.
- [System & Power](https://github.com/bpseditor/xfce4-system-power): reads `/proc` and `/sys`; Genmon shows telemetry and opens GTK settings.
- [Activity Tracker](https://github.com/bpseditor/xfce4-activity-tracker): Wnck tracks the active app; local SQLite stores daily time and named timers. No titles, URLs or keystrokes are stored. Desktop notifications announce timer completion.

Plugin sources are included in `bin/`; no sibling checkouts are needed. The panel uses English labels and updates app time every second. Machine-specific network names are replaced by automatic interface selection. Existing widget settings are retained. Log out and back in to start the tracker and reminder.

Desktop backups and `restore.py`: `~/.local/state/xfce4-setting/backups/`. Power changes have a separate root-owned recovery script. Qt session settings take effect after login.

Validation: `./install.sh --dry-run` and `python3 -m unittest discover -s tests`.

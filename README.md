# Data Budget [![Built for Omarchy: Plugin](https://raw.githubusercontent.com/tcballard/omarchy-badges/75975e5b5bf75e7ede3764bcd2950046f7abfe2c/badges/v1/omarchy-plugin.svg)](https://github.com/tcballard/omarchy-badges)


Track Wi-Fi, hotspot, and physical Ethernet data usage with a filling jar icon
and configurable budget alerts

Choose a connection, set a budget, and start tracking. Data Budget counts this
laptop's uploads and downloads. Omarchy's existing network menu continues to
manage connections.

<img width="481" height="769" alt="image" src="https://github.com/user-attachments/assets/7eccec93-a6d4-4352-a107-dc6c8527857b" />


## Features

- Rounded jar indicator that fills with usage and uses the theme's alert color
  at 100%. Hover for exact totals and percentages.
- A panel with downloaded, uploaded, and remaining data, plus editable budgets.
- Separate budgets for each selected NetworkManager connection profile.
- Session, daily, and calendar-month reset periods.
- Custom percentage alerts, with defaults of 50%, 80%, and 100%.
- Saved settings and current-period totals across shell restarts.
- Stop tracking without deleting a profile, or explicitly forget its saved data.
- Built-in bar support and a local IPC bridge for PeekBar.

No connection is automatically selected for tracking. Metered status is only a
hint; the plugin does not guess which Wi-Fi network is a phone hotspot. Alerts
never disconnect your network, throttle traffic, or pause applications.

## Requirements

| Dependency | Purpose |
| --- | --- |
| Omarchy Quattro with its plugin-capable shell | Hosts the widget and service |
| Quickshell and the standard `omarchy-shell` command | Panel, processes, and local IPC |
| Python 3 and `python-gobject` | Runs the local tracker through PyGObject |
| `libnm` and a running NetworkManager | Reads active connection metadata |
| Linux physical-interface counters under `/sys/class/net` | Measures received and transmitted bytes |
| A desktop notification service | Displays budget alerts |

The Python tracker uses system libraries, not pip dependencies. Check the
required Python binding before enabling the plugin:

```sh
python3 -c "import gi; gi.require_version('NM', '1.0'); from gi.repository import NM"
```

If this fails, install the missing dependencies through your system's normal
package-management process. The plugin does not download or install them.
No sudo or pkexec is required by the plugin.

PeekBar has been checked on the development desktop. Other replacement bars,
mixed-DPI layouts, and monitor hotplug have not been fully validated.

## Installation

Install and enable through Omarchy:

```sh
omarchy plugin install https://github.com/sanjyay/Data-budget.git --enable
```

The plugin appears as **Data Budget**. Its plugin ID is `sanjyay.hotspot-budget`.

## Removal

```sh
omarchy plugin remove sanjyay.hotspot-budget
```

To disable it without uninstalling:

```sh
omarchy plugin disable sanjyay.hotspot-budget
```

Saved budgets and usage are retained. Use **Forget saved profile** in the panel
before removal if you want to erase a profile's settings and totals.

## Usage

1. Click the jar icon and select a connection.
2. Enter **Budget · MB**. Units are decimal: 1000 MB equals 1 GB.
3. Choose **Each session**, **Daily**, or **Monthly**.
4. Enter comma-separated whole-number alert percentages, such as `50, 80, 100`.
5. Click **Start tracking**. Use **Save budget** to apply later changes.

Changing the reset period clears that profile's totals. Changing the budget size
preserves totals and re-arms its alerts. Daily periods reset at local midnight;
monthly periods reset on the first of the local calendar month. Session periods
reset on a new NetworkManager activation or system boot, not simply when you
reopen the panel or restart the shell.

**Stop tracking** retains the profile's settings and current-period totals;
normal period resets still apply. **Forget saved profile** requires a second
confirming click and deletes its settings and totals. A connected network remains
available in the picker after forgetting, but is no longer tracked.

An empty, dimmed jar means no active connection is tracked. An exclamation mark
indicates tracker unavailability. The jar stays full beyond the limit. If multiple
connections are tracked, its fill shows the highest usage percentage among active
profiles, rather than combining their independent allowances.

## Measurement limits

- Counts this laptop's interface traffic, including uploads, downloads, LAN
  traffic, and protocol overhead. It is not a carrier billing measurement or a
  total for other devices sharing a hotspot.
- Reads physical Wi-Fi and Ethernet interfaces. USB tethering works only when
  NetworkManager exposes it as a qualifying physical Ethernet device.
- Excludes VPN/tunnel interfaces to avoid counting their traffic twice; traffic
  carried through a physical interface still counts there.
- Samples every two seconds. Usage while the tracker is off is not reconstructed.
  Counter resets, connection changes, gaps, and period boundaries establish a new
  baseline; uncertain intervals are not charged. Very fast reconnects may be missed.
- Saves changing totals about every five seconds and on orderly shutdown. An
  abrupt termination can lose recent samples. Clock/timezone changes affect
  calendar periods; custom billing-cycle dates are not supported.
- Notification delivery depends on the desktop notification service and its DND
  behavior. Crossing several thresholds at once produces one alert for the
  highest threshold. Persisted warning markers prevent repeated attempts, but a
  crash or delivery failure can result in a missed notification.

## Privacy and stored data

The plugin reads local NetworkManager metadata and sysfs counters. It does not
read Wi-Fi passwords, inspect packets, record destinations or browsing history,
measure individual applications, or make external network requests. There are no
accounts, analytics, or remote services.

Selected profile UUIDs/names, budget settings, current-period totals, activation
identity, and warning markers are stored in:

```text
${XDG_STATE_HOME:-$HOME/.local/state}/hotspot-budget/
```

The directory uses mode `0700` and files use `0600`. Writes use an atomic
replacement and a lock prevents concurrent trackers. Damaged or unsupported
state is preserved and tracking stops rather than overwriting it. Network names
render as plain text and are omitted from notifications.

Like other community shell plugins, this code runs unsandboxed with your user's
permissions. These safeguards are not a security certification.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| No usage appears | Select the right connection and click **Start tracking**; earlier traffic is not counted. |
| Usage stays near zero | Your traffic may be using another active interface, such as Ethernet instead of Wi-Fi. |
| Tracker unavailable | Check the dependency command above, NetworkManager, and state-directory permissions. |
| State error | Back up the state directory before investigating; do not overwrite damaged state. |
| No notification | Check the configured thresholds and the desktop's DND settings. |
| Old panel after updating | Rescan plugins, then restart the shell if necessary. |

## Development and validation

```sh
./tools/check             # Python tests, manifest validation, and qmllint
./tools/check --portable  # Python tests without desktop dependencies
```

The suite includes 24 isolated accounting and persistence tests. Local QML and
installed-desktop checks supplement these tests; they do not establish every
hardware, notification, or multi-monitor scenario.

See [architecture](ARCHITECTURE.md), [security design](docs/security.md), and the
[verification record](docs/verification.md) for implementation details and known
validation limits.

## License

[MIT](LICENSE), copyright 2026 sanjyay. Independent community project.

# Data Budget

Track Wi-Fi, hotspot, and physical Ethernet data usage with a filling jar icon
and configurable budget alerts in Omarchy Quattro.

Choose a connection, set a budget, and start tracking. Data Budget counts this
laptop's uploads and downloads. Omarchy's existing network menu continues to
manage connections.

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

This project has not yet been published to the marketplace. The instructions
below install an already downloaded or checked-out copy locally; no public
repository URL is assumed.

From the repository root, review the source, then copy the runtime files into a
**new** user plugin directory:

```sh
(
  set -e
  plugin_dir="$HOME/.config/omarchy/plugins/sanjyay.hotspot-budget"
  mkdir -p "$HOME/.config/omarchy/plugins"
  mkdir "$plugin_dir"
  cp manifest.json Main.qml Service.qml TrackerBridge.qml LICENSE "$plugin_dir/"
  cp -R scripts "$plugin_dir/"
  omarchy-shell shell rescanPlugins
)
```

The `mkdir` deliberately fails if that plugin directory already exists, avoiding
an accidental overwrite. If copying fails partway through, inspect the partial
directory before retrying.

After discovery completes, enable the plugin:

```sh
omarchy plugin enable sanjyay.hotspot-budget --section right
```

If enabling reports an unknown plugin immediately after rescanning, wait for
discovery to finish and retry the enable command. If the bar still shows an old
version after an intentional update, use `omarchy restart shell`.

The display name is **Data Budget**. Its stable plugin ID remains
`sanjyay.hotspot-budget`, and its state directory remains `hotspot-budget` so
renaming the display does not discard existing installations or usage.

For a manual update, back up the installed plugin directory, disable the plugin,
and replace its runtime files with a reviewed version. Rescan and re-enable it.
Keep the state directory intact to retain budgets and totals. Installation and
updates do not modify built-in Wi-Fi files or NetworkManager profiles.

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

## Disable and remove

```sh
omarchy plugin disable sanjyay.hotspot-budget
omarchy plugin remove sanjyay.hotspot-budget
```

Saved budgets and usage are retained. To erase a particular profile, use
**Forget saved profile** before removal. To erase all stored data, disable the
plugin first, then delete only its `hotspot-budget` directory under the state
location above. Do not delete state while a tracker is running.

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

## License and marketplace status

[MIT](LICENSE), copyright 2026 sanjyay. Independent community project.

This README documents installation, removal, and dependencies as requested by the
marketplace's [submission guide](https://github.com/omacom/omarchy-plugin-marketplace/blob/main/SUBMISSION.md).
The project has not been submitted, listed, or granted marketplace verification.
Publication requires a public repository and the marketplace's validation and
maintainer approval; README completeness alone does not establish acceptance.

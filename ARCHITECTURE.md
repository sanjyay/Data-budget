# Architecture

`manifest.json` exposes a bar widget and a host-loaded service. The built-in bar
injects a scoped `shell` facade; Main.qml obtains only its own service through
`serviceFor`. Replacement bars use TrackerBridge.qml to query the service over
its explicit `sanjyay.hotspot-budget.tracker` IPC target every two seconds.
Only budget snapshots and the three validated budget actions are exposed.
The standard omarchy-shell command bounds IPC calls with its built-in timeout;
bridge requests never overlap and are stopped when the view is destroyed. Every monitor has a view, but Service.qml owns exactly one Python
Process. The OS state lock also rejects accidental concurrent trackers.

## Responsibilities

- **Main.qml:** theme-aware bar chip, keyboard-accessible scrollable popup, profile
  selection and explicit settings actions. External names render as plain text.
  Uses the host KeyboardPanel for placement, clamping and Escape/outside dismissal.
- **Service.qml:** lifecycle, bounded retries and watchdog, shared snapshots, and
  JSON command forwarding. The UI remains responsive during NM/storage operations.
- **scripts/tracker.py:** libnm connection observation, physical interface counters,
  two-second sampling, command validation, notifications and persistence scheduling.
- **scripts/model.py:** pure accounting and budget rules; independent of NM and QML.
- **scripts/store.py:** private directory, owner-only files, one-process lock,
  bounded reads, version validation, atomic replacements and fsync.

## Tracking identity

The profile UUID is the budget key. The activation identity combines boot ID,
NetworkManager D-Bus owner, active connection object path and interface index.
A profile with ambiguous simultaneous physical devices is not silently counted.
VPNs, bridges and virtual interfaces are excluded; no destination inspection is
needed. Physical counters still include LAN traffic and encrypted VPN overhead.

Each sample requires a matching preceding activation/interface and monotonically
increasing receive AND transmit counters. Boundaries, missing samples and resets
establish a baseline, charging zero for the uncertain interval. A persisted total
survives restarts; raw baselines deliberately do not. This avoids billing traffic
that happened while the plugin was disabled to a later connection.

NM connection-list changes trigger sampling; a two-second timer discovers state
transitions and reads counters. There is no polling over the network. State is
saved every five seconds when dirty, on commands/warnings, and graceful exit.
Session totals reset at a new activation. Calendar periods use the local clock.
Only the current period is retained, bounding disk usage and metadata retention.

## Protocol and lifecycle

The shell starts `/usr/bin/python3` with a local decoded path in an argument array.
No shell evaluates data. Commands are newline-delimited JSON with fixed actions:
`configure`, `stop`, `forget`. Input lines are capped at 8 KiB, accumulated input
at 16 KiB, profiles at 64, active devices at 32, and state at 256 KiB. Snapshots
are capped at 128 KiB with a 256 KiB pending-output cap. Output is nonblocking.

Parent stdin EOF, pipe failure, or SIGTERM/SIGINT stops the GLib loop and releases
the lock. The process has no descendants. QML stops it when the service is
unloaded. Failed starts retry with bounded exponential backoff (2–30 seconds);
a 12-second stale-response watchdog requests termination. There is no detached
background daemon or systemd unit. An uninterruptible filesystem/kernel operation
cannot be guaranteed to stop within a userspace deadline.

## Failure behavior

Corrupt, oversize, unsupported-version or non-private state fails closed without
replacing the existing file. Failed command writes restore the in-memory baseline
and settings; atomic replacement preserves the previous file until replacement.
A directory fsync failure after replacement can leave the new file installed even
though the operation reports failure; this is not a general rollback transaction.

Counter/persistence errors clear sample baselines and mark the UI unavailable;
tracking resumes with a fresh baseline after recovery. Notifications persist their
warning marker before issuing an asynchronous local D-Bus request. This gives
at-most-one attempted delivery per threshold per period, not guaranteed delivery.
A jump across multiple thresholds produces one notification for the highest.

## Compatibility

No built-in Wi-Fi files or user NM profiles are modified. Replacement bars without service lookup use the explicit IPC bridge; PeekBar
has been checked live. All display geometry
is delegated to the installed host panel; multi-monitor hotplug, portrait screens,
scaling and DND require physical desktop verification before release.

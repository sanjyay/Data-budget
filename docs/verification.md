# Verification — 2026-10-04

## Completed

- 24 isolated Python regression tests: accounting, resets, periods, thresholds,
  persistence, locks, symlinks, non-private files, corruption and atomic-write failure.
- Installed Omarchy manifest validator and qmllint.
- Real NetworkManager/libnm read-only smoke test, using temporary XDG state:
  discovered two physical connections, neither tracked by default, clean EOF exit.
- Real backend configure → stop → forget round trip with temporary state and a
  deliberately high budget; verified empty persisted profiles and clean exit.
  No NM settings changed and no test threshold notification was sent.
- QML component instantiated in a separate short-lived Wayland preview with a mock
  service; opened the panel and captured/visually inspected its sample-data content.
  It showed 420 MB of 1 GB, separate RX/TX, remaining budget and editable controls.
  This was not an installation into the user's shell.
- Instantiated the real Service.qml with two separate Main.qml views and temporary
  state; both resolved the same live tracker and received its connection rows.
  Destroyed both views and the service; no tracker process remained.
- Local source-pattern precheck using the marketplace scanner functions from
  commit `7520a0f08a418976c968be278299061cc284040c`: no findings or elevated
  capabilities detected. This did not run the server's snapshot-acquisition,
  compatibility or exact-commit publication workflow and is not verification.

The previews emitted host-portal registration, off-scene test-object and Qt shutdown timer warnings;
it had no component-load or QML runtime errors. An attempted offscreen preview
could not load the host PanelWindow backend, and an isolated headless compositor
could not initialize its graphics backend. The Wayland preview was used instead.

## Installed desktop check — 2026-10-04

Installed in the user's plugin directory, backed up shell.json, enabled on the
right, and restarted the shell to clear the earlier cached service. The active
bar is PeekBar; added a narrow local IPC fallback for its service-less facade.
Verified ready status with two physical connections, zero tracked profiles, and
exactly one tracker process. Opened and visually inspected the real panel in
PeekBar. No connection was automatically opted into tracking. The 24 regression
tests, manifest validator, and QML checks passed after the compatibility change.

## Not yet established

- Full uninstall lifecycle and additional bar implementations.
- Notification appearance/DND delivery, real phone tethering, physical reconnects,
  multiple-monitor hotplug, portrait bars, mixed DPI and long-running idle cost.
- Carrier billing agreement (the product deliberately counts interface traffic).
- Marketplace server validation, publication or maintainer approval.

## Release checklist

On a disposable desktop, enable the plugin, track a test connection, and verify:

1. Multiple bars share one tracker; adding/removing a monitor preserves totals.
2. 50/80/100 warnings are delivered at most once per period, including shell reload.
3. Daily totals survive a reconnect while session totals reset.
4. Turning tracking off excludes subsequent traffic. Re-enabling starts a baseline.
5. VPN traffic counts only once; LAN traffic is explicitly included.
6. Popup remains navigable by keyboard at small screen sizes and high scaling.
7. Disabling/removing the plugin ends its child process, releases the lock, and
   leaves unrelated config and network settings untouched.
8. NetworkManager outage, unwritable state and malformed state give visible errors.

Run `./tools/check` after changes. Desktop checks supplement the isolated tests;
static validation does not establish hardware or live integration behavior.

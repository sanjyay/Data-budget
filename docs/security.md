# Security and privacy design

The intended runtime authority is read-only NetworkManager device/activation
metadata, read-only sysfs interface counters, private plugin state and local
notification delivery. No NM secrets API, packet capture, Wi-Fi scan request,
Internet endpoint, analytics, root helper, shell command construction, firewall
rule, connection mutation, application suspension or service management is used.

Network names are untrusted display strings: control characters are removed,
lengths are bounded, and QML renders plain text (including dropdown delegates).
They never become commands or filesystem paths. UUIDs and budget settings have
strict validation. The counter path accepts only bounded interface-name syntax
and is rooted at `/sys/class/net`; only physical Wi-Fi/Ethernet devices qualify.

All persistence uses a plugin-owned 0700 directory and 0600 regular files.
No-follow opens, ownership/mode/type/link checks, held directory descriptors,
exclusive random staging files and an advisory lock reduce symlink, shared-temp,
corruption and concurrent-writer hazards. The parent XDG directory and current
user account are trusted; this cannot defend against malicious code already
running as the same user. JSON is data, not executable configuration.

Tracked network UUIDs/names are personal metadata. They are kept locally only,
with current-period totals and warning markers. No diagnostics print connection
names, credentials, environment dumps or traffic contents. The state is retained
on ordinary removal so reinstalling does not silently erase a budget; Forget
removes a selected profile's record with confirmation.

## Marketplace readiness

Reviewed marketplace SECURITY.md, SUBMISSION.md and VERIFICATION.md on 2026-10-04.
The project has a namespaced ID, root manifest/README/license, declared system
library dependencies, and explicit installation/removal instructions. Runtime
has no downloaded executables, unpinned remote execution, sudoers changes,
privileged process control, executable binary bundles or package manager calls.
CI checkout is pinned to a full commit. No automatic installation hooks exist.

This is a design review, not a security certification. Plugins share an
unsandboxed shell process; the marketplace baseline is a limited static check.
Marketplace acceptance requires its own exact-commit checks and maintainer
approval. Nothing has been submitted or published.

Sources:
- https://github.com/omacom/omarchy-plugin-marketplace/blob/main/SECURITY.md
- https://github.com/omacom/omarchy-plugin-marketplace/blob/main/SUBMISSION.md
- https://github.com/omacom/omarchy-plugin-marketplace/blob/main/VERIFICATION.md

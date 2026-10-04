#!/usr/bin/env python3
"""Shell-owned libnm observer. JSON lines on stdin/stdout; EOF releases all resources."""
import copy
from datetime import datetime
import json
import os
from pathlib import Path
import re
import signal
import sys
import time

from model import Accounting, clean_name, valid_uuid
from store import Store


def main():
    import gi
    gi.require_version('NM', '1.0')
    from gi.repository import Gio, GLib, GLibUnix, NM

    store = Store()
    try:
        engine = Accounting(store.load())
        loop = GLib.MainLoop()
        client = NM.Client.new(None)
        boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        observations = []
        error = ''
        notice = ''
        buffer = b''
        pending = b''
        output_watch = None
        last_save = time.monotonic()
        dirty = False
        os.set_blocking(0, False)
        os.set_blocking(1, False)
        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)

        def drain(*_):
            nonlocal pending, output_watch
            try:
                if pending:
                    pending = pending[os.write(1, pending):]
            except BlockingIOError:
                return True
            except (BrokenPipeError, OSError):
                loop.quit()
                return False
            if not pending:
                output_watch = None
                return False
            return True

        def emit(payload):
            nonlocal pending, output_watch
            data = (json.dumps(payload, ensure_ascii=True, separators=(',', ':')) + '\n').encode()
            if len(data) > 131072 or len(pending) + len(data) > 262144:
                loop.quit()  # Parent isn't reading; never grow a queue without bounds.
                return
            pending += data
            if output_watch is None:
                output_watch = GLib.io_add_watch(1, GLib.IO_OUT | GLib.IO_ERR | GLib.IO_HUP, drain)

        def notify(event):
            # No network name or other personal metadata in lock-screen notifications.
            bus.call('org.freedesktop.Notifications', '/org/freedesktop/Notifications',
                     'org.freedesktop.Notifications', 'Notify',
                     GLib.Variant('(susssasa{sv}i)', ('Data Budget', 0, 'network-wireless',
                         'Data budget warning', f"This laptop reached {event['threshold']}% of a tracked connection budget.",
                         [], {}, 8000)), None, Gio.DBusCallFlags.NONE, 2000, None, None, None)

        def discover():
            if not client.get_nm_running():
                raise ValueError('NetworkManager is unavailable. Tracking is paused.')
            found = []
            for active in client.get_active_connections():
                if active.get_state() != NM.ActiveConnectionState.ACTIVATED:
                    continue
                key = active.get_uuid()
                if not valid_uuid(key):
                    continue
                # Excludes VPN, bridges, containers, loopback, and virtual devices.
                devices = [d for d in active.get_devices() if d.get_device_type() in (NM.DeviceType.WIFI, NM.DeviceType.ETHERNET)]
                if len(devices) != 1:
                    continue
                device = devices[0]
                iface = device.get_iface()
                if not re.fullmatch(r'[A-Za-z0-9_.:-]{1,15}', iface or ''):
                    continue
                directory = Path('/sys/class/net') / iface
                if not (directory / 'device').exists():
                    continue
                try:
                    rx = int((directory / 'statistics/rx_bytes').read_text()[:32])
                    tx = int((directory / 'statistics/tx_bytes').read_text()[:32])
                    index = int((directory / 'ifindex').read_text()[:16])
                except (OSError, ValueError):
                    raise ValueError('An interface counter is unavailable. Tracking is paused.') from None
                if not (0 <= rx < 2**64 and 0 <= tx < 2**64):
                    raise ValueError('Invalid interface counter. Tracking is paused.')
                found.append({'uuid': key, 'name': clean_name(active.get_id()), 'iface': iface,
                              'rx': rx, 'tx': tx, 'session': f'{boot}:{client.get_dbus_name_owner()}:{active.get_path()}:{index}',
                              'type': 'Wi-Fi' if device.get_device_type() == NM.DeviceType.WIFI else 'Ethernet',
                              'metered': device.get_metered() in (NM.Metered.YES, NM.Metered.GUESS_YES)})
            if len({o['uuid'] for o in found}) != len(found):
                raise ValueError('A profile has multiple active interfaces; tracking paused.')
            if len(found) > 32:
                raise ValueError('More than 32 active physical connections; tracking paused.')
            return found

        def publish():
            rows = []
            profiles = engine.state['profiles']
            live = {o['uuid']: o for o in observations}
            for key in list(live) + [k for k in profiles if k not in live]:
                o, p = live.get(key), profiles.get(key)
                rows.append({'uuid': key, 'name': o['name'] if o else p['name'],
                             'active': o is not None, 'iface': o['iface'] if o else '',
                             'type': o['type'] if o else 'Saved connection',
                             'metered': o['metered'] if o else False,
                             'tracked': bool(p and p['enabled']),
                             'budget': p['budget'] if p else 1_000_000_000,
                             'period': p['period'] if p else 'session',
                             'thresholds': p['thresholds'] if p else [50, 80, 100],
                             'rx': p['rx'] if p else 0, 'tx': p['tx'] if p else 0})
            emit({'rows': rows, 'error': error, 'notice': notice, 'time': int(time.time())})

        def tick():
            nonlocal observations, error, last_save, dirty
            try:
                observations = discover()
                before = copy.deepcopy(engine.state)
                events = engine.sample(observations)
                dirty = dirty or engine.state != before
                # Persist warning markers before delivery so shell reloads do not repeat alerts.
                if dirty and (events or time.monotonic() - last_save >= 5):
                    store.save(engine.state)
                    last_save, dirty = time.monotonic(), False
                error = ''
                for event in events:
                    notify(event)
            except (ValueError, OSError, GLib.Error):
                error = 'Cannot read network state or save usage. Check NetworkManager and the private state directory.'
                observations = []
                engine.previous.clear()
            publish()
            return True

        def command(payload):
            nonlocal notice, dirty, last_save
            if not isinstance(payload, dict):
                raise ValueError('Invalid command.')
            action, key = payload.get('action'), payload.get('uuid')
            if not valid_uuid(key):
                raise ValueError('Select a connection first.')
            before = copy.deepcopy(engine.state)
            previous = dict(engine.previous)
            try:
                if action == 'configure':
                    o = next((o for o in observations if o['uuid'] == key), None)
                    saved = engine.state['profiles'].get(key)
                    if not o and not saved:
                        raise ValueError('Connection is no longer available. Reconnect and retry.')
                    engine.configure(key, o['name'] if o else saved['name'], payload.get('budget_mb'),
                                     payload.get('period'), payload.get('thresholds'))
                elif action == 'stop' and key in engine.state['profiles']:
                    engine.stop(key)
                elif action == 'forget':
                    engine.forget(key)
                else:
                    raise ValueError('Unknown action or connection.')
                store.save(engine.state)
                last_save, dirty = time.monotonic(), False
                notice = 'Saved.' if action != 'forget' else 'Saved profile and usage deleted.'
            except Exception:
                engine.state, engine.previous = before, previous
                raise
            tick()

        def read_input(_, condition):
            nonlocal buffer, notice
            try:
                data = os.read(0, 8192)
            except BlockingIOError:
                return True
            if not data:
                loop.quit()
                return False
            buffer += data
            if len(buffer) > 16384:
                loop.quit()
                return False
            while b'\n' in buffer:
                line, buffer = buffer.split(b'\n', 1)
                if len(line) > 8192:
                    loop.quit()
                    return False
                try:
                    command(json.loads(line))
                except (ValueError, KeyError, TypeError, OSError):
                    notice = 'Could not save. Use a valid budget, period and thresholds; check state-file permissions.'
                    publish()
            return True

        GLib.io_add_watch(0, GLib.IO_IN | GLib.IO_HUP | GLib.IO_ERR, read_input)
        GLibUnix.signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, lambda: (loop.quit(), False)[1])
        GLibUnix.signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, lambda: (loop.quit(), False)[1])
        client.connect('notify::active-connections', lambda *_: tick())
        client.connect('notify::nm-running', lambda *_: tick())
        GLib.timeout_add(2000, tick)
        tick()
        try:
            loop.run()
        finally:
            if dirty:
                store.save(engine.state)
    finally:
        store.close()


if __name__ == '__main__':
    try:
        main()
    except (ImportError, ValueError, OSError) as exc:
        # Do not dump paths, saved network names or environment into the host log.
        print(json.dumps({'rows': [], 'error': 'Tracker unavailable: check python-gobject, libnm, NetworkManager, and private state permissions.', 'notice': ''}), flush=True)
        sys.exit(1)

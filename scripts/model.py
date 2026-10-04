"""Pure accounting; only samples from explicit physical connection profiles count."""
from datetime import datetime
import math
import uuid

MAX_PROFILES = 64
MAX_BYTES = 2**63 - 1


def integer(value, low, high):
    return type(value) is int and low <= value <= high


def valid_uuid(value):
    try:
        return isinstance(value, str) and str(uuid.UUID(value)) == value.lower()
    except (ValueError, AttributeError):
        return False


def validate_state(state):
    if not isinstance(state, dict) or type(state.get('version')) is not int or state.get('version') != 1:
        raise ValueError('Unsupported or damaged state; existing file has been preserved.')
    profiles = state.get('profiles')
    if not isinstance(profiles, dict) or len(profiles) > MAX_PROFILES:
        raise ValueError('Invalid profile state.')
    for key, p in profiles.items():
        if not valid_uuid(key) or not isinstance(p, dict):
            raise ValueError('Invalid saved profile.')
        if not isinstance(p.get('name'), str) or len(p['name']) > 160:
            raise ValueError('Invalid profile name.')
        if type(p.get('enabled')) is not bool or p.get('period') not in ('session', 'daily', 'monthly'):
            raise ValueError('Invalid tracking settings.')
        if not integer(p.get('budget'), 1_000_000, 1_000_000_000_000_000):
            raise ValueError('Invalid budget.')
        for field in ('rx', 'tx'):
            if not integer(p.get(field), 0, MAX_BYTES):
                raise ValueError('Invalid usage total.')
        for field in ('period_key', 'session'):
            if not isinstance(p.get(field), str) or len(p[field]) > 256:
                raise ValueError('Invalid accounting period.')
        for field in ('thresholds', 'warned'):
            values = p.get(field)
            if not isinstance(values, list) or len(values) > 10 or not all(integer(v, 1, 100) for v in values):
                raise ValueError('Invalid thresholds.')
    return state


def period_key(mode, now, session):
    if mode == 'session':
        return session
    return now.strftime('%Y-%m-%d' if mode == 'daily' else '%Y-%m')


class Accounting:
    def __init__(self, state=None):
        self.state = validate_state(state) if state is not None else {'version': 1, 'profiles': {}}
        self.previous = {}

    def configure(self, key, name, budget_mb, period, thresholds):
        if not valid_uuid(key) or period not in ('session', 'daily', 'monthly'):
            raise ValueError('Choose a valid connection and budget period.')
        if type(budget_mb) not in (int, float) or not math.isfinite(budget_mb) or not 1 <= budget_mb <= 1_000_000_000:
            raise ValueError('Budget must be between 1 and 1,000,000,000 MB.')
        if not isinstance(thresholds, list) or not 1 <= len(thresholds) <= 10 or not all(integer(v, 1, 100) for v in thresholds):
            raise ValueError('Enter 1–10 whole-number thresholds from 1 to 100.')
        profiles = self.state['profiles']
        if key not in profiles and len(profiles) >= MAX_PROFILES:
            raise ValueError('Maximum 64 saved profiles. Forget an unused profile first.')
        p = profiles.get(key)
        if p is None:
            p = {'rx': 0, 'tx': 0, 'period_key': '', 'session': '', 'warned': []}
            profiles[key] = p
        if p.get('period', period) != period:
            p.update(rx=0, tx=0, period_key='', warned=[])
            self.previous.pop(key, None)
        if not p.get('enabled', False):
            self.previous.pop(key, None)
        new_budget = int(budget_mb * 1_000_000)
        new_thresholds = sorted(set(thresholds))
        if p.get('budget') != new_budget or p.get('thresholds') != new_thresholds:
            p['warned'] = []
        p.update(name=clean_name(name), budget=new_budget, period=period,
                 thresholds=new_thresholds, enabled=True)

    def stop(self, key):
        self.state['profiles'][key]['enabled'] = False
        self.previous.pop(key, None)

    def forget(self, key):
        self.state['profiles'].pop(key, None)
        self.previous.pop(key, None)

    def sample(self, observations, now=None):
        """Never bridge counter resets, activation changes, gaps or period boundaries."""
        now = now or datetime.now().astimezone()
        events = []
        profiles = self.state['profiles']
        live = {o['uuid']: o for o in observations}
        for key in list(self.previous):
            if key not in live:
                self.previous.pop(key)
        for key, p in profiles.items():
            o = live.get(key)
            if o:
                p['session'] = o['session']
            elif p['period'] == 'session':
                continue
            token = period_key(p['period'], now, p['session'])
            if token != p['period_key']:
                p.update(rx=0, tx=0, warned=[], period_key=token)
                self.previous.pop(key, None)
            if not o or not p['enabled']:
                continue
            current = (o['session'], o['iface'], o['rx'], o['tx'])
            previous = self.previous.get(key)
            if previous and previous[:2] == current[:2] and current[2] >= previous[2] and current[3] >= previous[3]:
                p['rx'] = min(MAX_BYTES, p['rx'] + current[2] - previous[2])
                p['tx'] = min(MAX_BYTES, p['tx'] + current[3] - previous[3])
            self.previous[key] = current
            crossed = [t for t in p['thresholds'] if t not in p['warned'] and (p['rx'] + p['tx']) * 100 >= p['budget'] * t]
            if crossed:
                p['warned'] = sorted(set(p['warned'] + crossed))
                events.append({'uuid': key, 'threshold': max(crossed)})
        return events


def clean_name(value):
    return ''.join(c for c in str(value) if c.isprintable())[:160]

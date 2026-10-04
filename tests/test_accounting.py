import copy
from datetime import datetime
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from model import Accounting, validate_state

KEY = '11111111-1111-4111-8111-111111111111'
OTHER = '22222222-2222-4222-8222-222222222222'
NOW = datetime(2026, 10, 4, 12)


def sample(rx, tx=0, session='activation-1', key=KEY, iface='wlan0'):
    return {'uuid': key, 'rx': rx, 'tx': tx, 'session': session, 'iface': iface}


class AccountingTests(unittest.TestCase):
    def setUp(self):
        self.engine = Accounting()
        self.engine.configure(KEY, 'Phone', 1, 'daily', [50, 80, 100])

    @property
    def p(self):
        return self.engine.state['profiles'][KEY]

    def test_only_selected_connection_counts_and_uploads_count(self):
        self.engine.sample([sample(100), sample(500, key=OTHER)], NOW)
        self.engine.sample([sample(400, 50), sample(99999, key=OTHER)], NOW)
        self.assertEqual((self.p['rx'], self.p['tx']), (300, 50))
        self.assertNotIn(OTHER, self.engine.state['profiles'])

    def test_counter_reset_never_adds_negative_or_huge_delta(self):
        for rx, tx in [(900, 800), (1000, 900), (2, 3), (12, 13)]:
            self.engine.sample([sample(rx, tx)], NOW)
        self.assertEqual((self.p['rx'], self.p['tx']), (110, 110))

    def test_reconnect_excludes_other_connection_bytes(self):
        self.engine.sample([sample(100)], NOW)
        self.engine.sample([sample(200)], NOW)
        self.engine.sample([], NOW)
        self.engine.sample([sample(999999, session='activation-2')], NOW)
        self.engine.sample([sample(1000099, session='activation-2')], NOW)
        self.assertEqual(self.p['rx'], 200)

    def test_session_resets_on_new_activation_not_shell_restart(self):
        self.engine.configure(KEY, 'Phone', 1, 'session', [50, 80, 100])
        self.engine.sample([sample(0)], NOW)
        self.engine.sample([sample(100)], NOW)
        restored = Accounting(copy.deepcopy(self.engine.state))
        restored.sample([sample(500)], NOW)
        self.assertEqual(restored.state['profiles'][KEY]['rx'], 100)
        restored.sample([sample(600, session='activation-2')], NOW)
        self.assertEqual(restored.state['profiles'][KEY]['rx'], 0)

    def test_midnight_resets_without_assigning_cross_boundary_bytes(self):
        self.engine.sample([sample(0)], NOW)
        self.engine.sample([sample(500)], NOW)
        self.engine.sample([sample(700)], datetime(2026, 10, 5))
        self.assertEqual(self.p['rx'], 0)
        self.engine.sample([sample(800)], datetime(2026, 10, 5))
        self.assertEqual(self.p['rx'], 100)

    def test_calendar_month_resets_offline(self):
        self.engine.configure(KEY, 'Phone', 1, 'monthly', [50])
        self.engine.sample([sample(0)], NOW)
        self.engine.sample([sample(100)], NOW)
        self.engine.sample([], datetime(2026, 11, 1))
        self.assertEqual(self.p['rx'], 0)
        self.assertEqual(self.p['period_key'], '2026-11')

    def test_thresholds_coalesce_and_are_persisted(self):
        self.engine.sample([sample(0)], NOW)
        events = self.engine.sample([sample(850000)], NOW)
        self.assertEqual(events, [{'uuid': KEY, 'threshold': 80}])
        self.assertEqual(self.p['warned'], [50, 80])
        self.assertEqual(self.engine.sample([sample(900000)], NOW), [])
        restored = Accounting(copy.deepcopy(self.engine.state))
        self.assertEqual(restored.sample([sample(900000)], NOW), [])
        self.assertEqual(restored.sample([sample(1100000)], NOW)[0]['threshold'], 100)

    def test_stopping_does_not_count_gap(self):
        self.engine.sample([sample(0)], NOW)
        self.engine.sample([sample(100)], NOW)
        self.engine.stop(KEY)
        self.engine.sample([sample(99999)], NOW)
        self.engine.configure(KEY, 'Phone', 1, 'daily', [50, 80, 100])
        self.engine.sample([sample(100000)], NOW)
        self.engine.sample([sample(100100)], NOW)
        self.assertEqual(self.p['rx'], 200)

    def test_edit_budget_keeps_usage_and_reassesses_threshold(self):
        self.engine.sample([sample(0)], NOW)
        self.engine.sample([sample(600000)], NOW)
        self.engine.configure(KEY, 'Phone', 2, 'daily', [50])
        self.assertEqual(self.p['rx'], 600000)
        self.assertEqual(self.engine.sample([sample(600000)], NOW), [])

    def test_forget_removes_data(self):
        self.engine.forget(KEY)
        self.assertEqual(self.engine.state['profiles'], {})
        self.assertEqual(self.engine.previous, {})

    def test_invalid_input_does_not_mutate(self):
        before = copy.deepcopy(self.engine.state)
        for budget in (True, float('nan'), float('inf'), 0, -1, '1000'):
            with self.assertRaises(ValueError):
                self.engine.configure(KEY, 'Phone', budget, 'daily', [50])
        for thresholds in ([], [0], [101], [True], ['50']):
            with self.assertRaises(ValueError):
                self.engine.configure(KEY, 'Phone', 1, 'daily', thresholds)
        self.assertEqual(self.engine.state, before)

    def test_interface_change_creates_baseline(self):
        self.engine.sample([sample(0)], NOW)
        self.engine.sample([sample(100)], NOW)
        self.engine.sample([sample(999999, iface='eth0')], NOW)
        self.assertEqual(self.p['rx'], 100)

    def test_calendar_reset_rearms_warning(self):
        self.engine.sample([sample(0)], NOW)
        self.engine.sample([sample(600000)], NOW)
        tomorrow = datetime(2026, 10, 5)
        self.engine.sample([sample(700000)], tomorrow)
        self.assertEqual(self.p['warned'], [])
        self.assertEqual(self.engine.sample([sample(1300000)], tomorrow)[0]['threshold'], 50)

    def test_schema_boolean_is_not_a_version(self):
        with self.assertRaises(ValueError):
            Accounting({'version': True, 'profiles': {}})

    def test_state_rejects_future_schema_and_bad_counters(self):
        with self.assertRaises(ValueError):
            Accounting({'version': 2, 'profiles': {}})
        self.p['rx'] = -10
        with self.assertRaises(ValueError):
            validate_state(self.engine.state)


if __name__ == '__main__':
    unittest.main()

"""Pass Window: rule logic, 8 UNREVIEWED demo scenarios, gating, visitor mode
stores nothing, and SPINE_SPEC test 21 (both flags off = demo flow unchanged)."""

import ast
import json
from io import StringIO
from pathlib import Path
from unittest import mock

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from strength_app import v1_pass_window_visitor_views
from strength_app.mind_lab import config
from strength_app.mind_lab import pass_window as pw
from strength_app.mind_lab.pass_window_data import load_scenarios
from strength_app.models import GameSession, MindLabCheckIn
from strength_app.tests.test_mind_lab import make_athlete

B, A, W, T = pw.BEST, pw.ACCEPTABLE, pw.WRONG, pw.TIMEOUT


class TestScenarios(SimpleTestCase):
    def test_eight_scenarios_all_unreviewed(self):
        sc = load_scenarios()
        self.assertEqual([s['id'] for s in sc], [f'PD-00{i}' for i in range(1, 9)])
        self.assertEqual({s['review'] for s in sc}, {'UNREVIEWED'})

    def test_correct_is_one_of_the_options(self):
        for s in load_scenarios():
            self.assertIn(s['correct'], s['options'], s['id'])
            for a in s['acceptable']:
                self.assertIn(a, s['options'], s['id'])


class TestScoring(SimpleTestCase):
    def setUp(self):
        self.by_id = {s['id']: s for s in load_scenarios()}

    def test_best_acceptable_wrong_timeout(self):
        sc = self.by_id['PD-008']
        self.assertEqual(pw.score_choice(sc, 'T1:direct'), B)
        self.assertEqual(pw.score_choice(sc, 'T3:direct'), A)
        self.assertEqual(pw.score_choice(sc, 'T2:direct'), W)
        self.assertEqual(pw.score_choice(sc, 'T9:direct'), W)
        self.assertEqual(pw.score_trial(sc, 'T1:direct', True), T)

    def test_acceptable_not_counted_by_default(self):
        self.assertFalse(config.PASS_WINDOW_ACCEPTABLE_COUNTS_AS_CORRECT)
        self.assertFalse(pw.counts_as_correct(A))
        with mock.patch.object(config, 'PASS_WINDOW_ACCEPTABLE_COUNTS_AS_CORRECT', True):
            self.assertTrue(pw.counts_as_correct(A))

    def test_trial_order_cycles_the_level_pool(self):
        sc = load_scenarios()
        self.assertEqual(pw.trial_order(sc, 2, 3), ['PD-004', 'PD-005', 'PD-004'])
        self.assertEqual(pw.trial_order(sc, 3, 2), ['PD-003', 'PD-003'])
        self.assertEqual(pw.trial_order(sc, 9, 3), [])

    def test_factors_are_the_ladder(self):
        self.assertEqual(pw.LEVEL_FACTORS, {1: 0.3, 2: 0.5, 3: 0.7, 4: 0.85, 5: 1.0})


class TestAdaptiveRule(SimpleTestCase):
    """Defaults: block 4, up 90% x 2 blocks, no timeouts; down <70% x 2 blocks or 2 timeouts."""

    def test_raise_after_two_perfect_blocks(self):
        self.assertEqual(pw.next_level(2, [B] * 8), 3)

    def test_one_good_block_holds(self):
        self.assertEqual(pw.next_level(2, [B] * 4), 2)

    def test_timeout_blocks_a_raise(self):
        self.assertEqual(pw.next_level(2, [B, B, B, T] + [B] * 4), 2)

    def test_two_timeouts_drop(self):
        self.assertEqual(pw.next_level(3, [B, T, B, B, B, T, B, B]), 2)

    def test_two_low_blocks_drop(self):
        self.assertEqual(pw.next_level(3, [W, W, W, B, W, W, B, B]), 2)

    def test_middle_holds(self):
        self.assertEqual(pw.next_level(3, [B, B, B, W, B, B, B, B]), 3)

    def test_exactly_at_down_threshold_holds(self):
        # 70% of 4 is 2.8, so 3 of 4 (75%) holds and 2 of 4 (50%) is low.
        self.assertEqual(pw.next_level(3, [B, B, B, W, B, B, B, W]), 3)

    def test_partial_block_ignored(self):
        self.assertEqual(pw.next_level(2, [B] * 7), 2)

    def test_never_more_than_one_level_and_clamped(self):
        self.assertEqual(pw.next_level(5, [B] * 8), 5)
        self.assertEqual(pw.next_level(1, [T] * 8), 1)
        self.assertEqual(pw.next_level(2, [B] * 40), 3)
        self.assertEqual(pw.next_level(4, [W] * 40), 3)

    def test_drop_beats_raise(self):
        self.assertEqual(pw.next_level(3, [B] * 6 + [T, T]), 2)

    def test_hold_flag_holds(self):
        self.assertEqual(pw.next_level(2, [B] * 8, hold=True), 2)
        self.assertEqual(pw.next_level(3, [W] * 8, hold=True), 3)

    def test_defaults_are_conservative(self):
        self.assertGreaterEqual(config.PASS_WINDOW_ACCURACY_UP_PCT, 90)
        self.assertGreaterEqual(config.PASS_WINDOW_ACCURACY_DOWN_PCT, 70)
        self.assertGreaterEqual(config.PASS_WINDOW_BLOCKS_TO_RAISE, 2)
        self.assertLessEqual(config.PASS_WINDOW_SESSION_MAX_S, 90)


class TestCleanTrials(SimpleTestCase):
    def good(self, **kw):
        t = {'scenario_id': 'PD-004', 'chosen': 'T3:direct', 'timeout': False, 'decision_ms': 900}
        t.update(kw)
        return t

    def test_rejects_bad(self):
        sc = load_scenarios()
        for bad in ([], 'x', [1], [self.good(scenario_id='PD-999')],
                    [self.good(timeout='no')], [self.good(decision_ms=True)],
                    [self.good(decision_ms=-1)], [self.good(decision_ms=float('nan'))],
                    [self.good(chosen=None)], [self.good(timeout=True)],
                    [self.good()] * 99):
            with self.assertRaises(ValueError, msg=bad):
                pw.clean_trials(bad, sc, 8)

    def test_timeout_has_no_choice_or_time(self):
        out = pw.clean_trials([self.good(timeout=True, chosen=None, decision_ms=None)],
                              load_scenarios(), 8)
        self.assertTrue(out[0]['timeout'])

    def test_session_result_ignores_client_claims(self):
        trials = [self.good(), self.good(chosen='T1:direct', decision_ms=500)]
        r = pw.session_result(2, trials, load_scenarios())
        self.assertEqual((r['n_trials'], r['accuracy'], r['median_rt_ms']), (2, 0.5, 700.0))


def _checkin(athlete, sleep):
    MindLabCheckIn.objects.create(
        athlete=athlete, sleep_bucket=sleep, stress=2, energy=4, focus=4,
        pain_light='green', gate_applied='full', day_label='full')


@override_settings(MIND_LAB_ENABLED=True)
class TestGating(TestCase):
    def setUp(self):
        self.athlete, _ = make_athlete('PWATH1')
        s = self.client.session
        s['patient_id'] = self.athlete.patient_id
        s.save()
        self.url = reverse('pass_window')
        self.save_url = reverse('pass_window_save')
        self.trials = [{'scenario_id': 'PD-004', 'chosen': 'T3:direct',
                        'timeout': False, 'decision_ms': 800}] * 8

    def save(self):
        return self.client.post(self.save_url, data=json.dumps({'summary': {'trials': self.trials}}),
                                content_type='application/json')

    def test_no_checkin_yet_not_playable(self):  # checkin_breath_only
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 403)
        self.assertNotContains(resp, 'mindLabHost', status_code=403)
        self.assertEqual(self.save().status_code, 403)
        self.assertEqual(GameSession.objects.count(), 0)

    def test_recovery_only_not_playable(self):
        _checkin(self.athlete, 'under_5')
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(self.save().status_code, 403)
        self.assertEqual(GameSession.objects.count(), 0)

    def test_red_pain_not_playable(self):
        _checkin(self.athlete, 'over_6')
        with mock.patch('strength_app.mind_lab.day_mode.pain_light_for', return_value='red'):
            self.assertEqual(self.client.get(self.url).status_code, 403)
            self.assertEqual(self.save().status_code, 403)

    def test_full_day_plays_and_server_sets_level(self):
        _checkin(self.athlete, 'over_6')
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Demo scenarios')
        self.assertContains(resp, 'not a return-to-play test')
        # Level 1 start, so PD-004 (a Level 2 scenario) is scored but level stays server-set.
        self.assertEqual(self.save().status_code, 200)
        gs = GameSession.objects.get()
        self.assertEqual((gs.level, gs.slowmo_factor), (1, 0.3))
        self.assertEqual(gs.summary['next_level'], 2)
        self.assertEqual(gs.summary['scenario_review'], 'UNREVIEWED')
        # The next page load starts at the stored next level.
        self.assertIn('"level": 2', self.client.get(self.url).content.decode().replace('\\u0022', '"'))

    def test_shortened_day_plays_but_level_holds(self):
        _checkin(self.athlete, '5_to_6')
        self.assertEqual(self.save().status_code, 200)
        self.assertEqual(GameSession.objects.get().summary['next_level'], 1)

    def test_bad_trials_400_nothing_stored(self):
        _checkin(self.athlete, 'over_6')
        self.trials = [{'scenario_id': 'nope'}]
        self.assertEqual(self.save().status_code, 400)
        self.assertEqual(GameSession.objects.count(), 0)

    def test_signed_out(self):
        self.client.session.flush()
        self.assertEqual(self.client.get(self.url).status_code, 302)
        self.assertEqual(self.save().status_code, 403)


@override_settings(MIND_LAB_ENABLED=True)
class TestVisitorStoresNothing(TestCase):
    def test_visitor_page_is_fixed_and_has_no_save_url(self):
        resp = self.client.get(reverse('pass_window_visitor'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Nothing is saved.')
        self.assertContains(resp, 'Demo scenarios')
        cfg = resp.context['config_json']
        data = json.loads(cfg)
        self.assertEqual(data['level'], 2)
        self.assertEqual(data['order'], ['PD-004', 'PD-005', 'PD-004'])
        self.assertIsNone(data['save_url'])
        self.assertEqual(GameSession.objects.count(), 0)
        self.assertEqual(MindLabCheckIn.objects.count(), 0)
        self.assertNotIn('sessionid', self.client.cookies)

    def test_visitor_cannot_post(self):
        self.assertEqual(self.client.post(reverse('pass_window_visitor'), {}).status_code, 200)
        self.assertEqual(GameSession.objects.count(), 0)

    def test_visitor_module_has_no_write_path(self):
        """Structural: no models import, no session use, no write call."""
        tree = ast.parse(Path(v1_pass_window_visitor_views.__file__).read_text())
        banned_calls = {'save', 'create', 'bulk_create', 'update', 'delete',
                        'get_or_create', 'update_or_create', 'execute'}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                self.assertNotIn('models', (node.module or '').split('.'))
                self.assertNotIn('models', [a.name for a in node.names])
            if isinstance(node, ast.Attribute):
                self.assertNotIn(node.attr, banned_calls)
                self.assertNotEqual(node.attr, 'session')
                self.assertNotEqual(node.attr, 'objects')

    def test_visitor_imports_stay_model_free(self):
        """The helpers the visitor module pulls in must not import models either."""
        import strength_app.mind_lab.pass_window_data as data
        for mod in (data, pw):
            tree = ast.parse(Path(mod.__file__).read_text())
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    names = [a.name for a in node.names] + [getattr(node, 'module', '') or '']
                    self.assertFalse(any('django' in n or 'models' in n for n in names), names)


class TestFlagsOffDemoFlowUnchanged(TestCase):
    """SPINE_SPEC test 21: RTP_ENABLED and MIND_LAB_ENABLED both False."""

    @override_settings(RTP_ENABLED=False, MIND_LAB_ENABLED=False)
    def test_demo_flow_unchanged_and_new_pages_404(self):
        call_command('seed_football_demo', stdout=StringIO())
        resp = self.client.post('/login/', {'phone': '9000000005', 'password': 'athlete'})
        self.assertIn(resp.status_code, (200, 302))
        for path in ('/athlete/today/', '/athlete/progress/', '/athlete/profile/'):
            page = self.client.get(path)
            self.assertEqual(page.status_code, 200, path)
            html = page.content.decode()
            self.assertNotIn('Pass Window', html, path)
            self.assertNotIn('Mind Lab', html, path)
        self.assertIn('DEMO DATA', self.client.get('/athlete/today/').content.decode())
        for name in ('mind_lab_checkin', 'mind_lab_visitor', 'pass_window',
                     'pass_window_visitor'):
            self.assertEqual(self.client.get(reverse(name)).status_code, 404, name)
        self.assertEqual(self.client.post(reverse('pass_window_save'), {}).status_code, 404)
        self.assertEqual(GameSession.objects.count(), 0)
        self.assertEqual(MindLabCheckIn.objects.count(), 0)

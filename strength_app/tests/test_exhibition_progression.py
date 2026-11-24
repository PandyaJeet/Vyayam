"""/exhibition/progression/: live engine, rolled back, nothing stored."""
import re
import threading
from datetime import date, timedelta
from unittest import mock

from django.apps import apps
from django.db.models.signals import post_save, pre_save
from django.test import TestCase, override_settings
from django.urls import reverse

from strength_app import v1_exhibition_progression as vp
from strength_app import v1_prescription_engine as engine
from strength_app import v1_session_views
from strength_app.models import (
    ExerciseExecution, PainEvent, PatientFamilyCapability, PatientProfile,
    PeriodisationState, SessionFeedback, StrengthProfile, WorkoutSession,
)
from strength_app.rtp.models import InjuryEpisode
from strength_app.v1_football_constants import LSI_THRESHOLDS
from strength_app.v1_onboarding_views import _compute_asymmetry_raw

URL = '/exhibition/progression/'
BANNED = ('fracture', 'cleared', 'clearance', 'healing', 'diagnos')


def _row_counts():
    return {m._meta.label: m.objects.count() for m in apps.get_models()
            if m._meta.managed and not m._meta.proxy}


class Recorder:
    """Wraps generate_v1_session: records what the engine was given."""

    def __init__(self):
        self.calls = []
        self.real = engine.generate_v1_session

    def __call__(self, patient):
        self.calls.append({
            'id': patient.patient_id, 'phone': patient.phone,
            'absolute_stop': patient.absolute_stop,
            'red_flags': list(patient.red_flags_json or []),
            'football': hasattr(patient, 'football_profile') and bool(
                getattr(patient, 'athlete_tier_active', False)),
            'episodes': InjuryEpisode.objects.count(),
            'pain': PainEvent.objects.count(),
        })
        return self.real(patient)


@override_settings(EXHIBITION_MODE=False)
class FlagOffTests(TestCase):
    def test_404(self):
        self.assertEqual(self.client.get(URL).status_code, 404)


@override_settings(EXHIBITION_MODE=True)
class ProgressionPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # One build shared by the read-only checks below.
        cls.rec = Recorder()
        with mock.patch.object(vp, 'generate_v1_session', cls.rec):
            cls.page = vp.build_page()

    # -- access, storage ------------------------------------------------------
    def test_anonymous_200_and_index_links_to_it(self):
        self.assertEqual(self.client.get(URL).status_code, 200)
        self.assertContains(self.client.get('/exhibition/'), reverse('exhibition_progression'))

    def test_row_counts_equal_before_and_after_two_calls_in_a_row(self):
        before = _row_counts()
        self.assertEqual(self.client.get(URL).status_code, 200)
        self.assertEqual(_row_counts(), before)
        self.assertEqual(self.client.get(URL).status_code, 200)
        self.assertEqual(_row_counts(), before)

    def test_no_signal_receivers_on_created_models(self):
        for m in (PatientProfile, StrengthProfile, PeriodisationState, WorkoutSession,
                  SessionFeedback, ExerciseExecution, PatientFamilyCapability):
            self.assertFalse(post_save.has_listeners(m), m)
            self.assertFalse(pre_save.has_listeners(m), m)

    def test_view_body_is_under_one_module_level_lock(self):
        self.assertIsInstance(vp._LOCK, type(threading.Lock()))
        with mock.patch.object(vp, '_LOCK', mock.MagicMock()) as lock:
            self.client.get(URL)
        lock.__enter__.assert_called_once()

    # -- engine entry point ---------------------------------------------------
    def test_same_entry_point_as_the_patient_session_view(self):
        self.assertIs(v1_session_views.generate_v1_session, engine.generate_v1_session)
        self.assertIs(vp.generate_v1_session, engine.generate_v1_session)

    def test_engine_runs_twice_per_request_with_unique_ids(self):
        calls = self.rec.calls
        self.assertEqual(len(calls), 2)
        for c in calls:
            self.assertTrue(c['id'].startswith('EXHDEMO_'))
            self.assertLessEqual(len(c['id']), 20)
            self.assertLessEqual(len(c['phone']), 20)
        rec2 = Recorder()
        with mock.patch.object(vp, 'generate_v1_session', rec2):
            vp.build_page()
        self.assertFalse({c['id'] for c in calls} & {c['id'] for c in rec2.calls})
        self.assertFalse({c['phone'] for c in calls} & {c['phone'] for c in rec2.calls})

    def test_persona_has_no_football_injury_pain_or_stop(self):
        for c in self.rec.calls:
            self.assertFalse(c['absolute_stop'])
            self.assertNotIn('acute_fracture', c['red_flags'])
            self.assertEqual(c['red_flags'], [])
            self.assertFalse(c['football'])
            self.assertEqual(c['episodes'], 0)
            self.assertEqual(c['pain'], 0)

    def test_session_budget_is_a_value_the_onboarding_slider_can_send(self):
        # onboarding_equipment.html: min=20 max=90 step=5. Lunge rows must survive it.
        html = open('strength_app/templates/strength_app/onboarding_equipment.html').read()
        self.assertRegex(html, r'min="20"[^>]*max="90"|max="90"[^>]*min="20"')
        minutes = set()
        real = engine.generate_v1_session

        def spy(patient):
            minutes.add(patient.session_duration_minutes)
            return real(patient)
        with mock.patch.object(vp, 'generate_v1_session', spy):
            page = vp.build_page()
        self.assertEqual(minutes, {90})
        for key in ('run_a', 'run_b'):
            self.assertTrue([r for r in page[key]['rows'] if r['pattern'] == 'lunge'], key)

    def test_training_age_is_what_onboarding_maps_intermediate_to(self):
        src = open('strength_app/v1_onboarding_views.py').read()
        self.assertIn("'intermediate': 18", src)
        ages = set()
        real = engine.generate_v1_session

        def spy(patient):
            ages.add((patient.training_history, patient.training_age_months))
            return real(patient)
        with mock.patch.object(vp, 'generate_v1_session', spy):
            vp.build_page()
        self.assertEqual(ages, {('intermediate', 18)})

    def test_rtp_flag_is_unset(self):
        from django.conf import settings
        self.assertFalse(getattr(settings, 'RTP_ENABLED', False))

    def test_moving_the_lunge_pair_changes_weak_side_sets(self):
        # Proves the engine is live: another band, another extra-set count.
        def weak_extra(page):
            rows = [r for r in page['run_b']['rows'] if r['pattern'] == 'lunge' and r['unilateral']]
            return {r['sets_weak'] - r['sets'] for r in rows}
        self.assertEqual(weak_extra(self.page), {1})
        with mock.patch.object(vp, 'LUNGE_NOW', (6, 12)):
            self.assertEqual(weak_extra(vp.build_page()), {2})
        with mock.patch.object(vp, 'LUNGE_NOW', (11, 12)):
            rows = [r for r in vp.build_page()['run_b']['rows'] if r['pattern'] == 'lunge']
            self.assertTrue(rows)
            self.assertTrue(all(not r['sets_weak'] and r['extra'] == 0 for r in rows))

    def test_lunge_is_in_the_plan_whatever_the_day_of_the_week(self):
        # The engine picks today's patterns from the count of sessions this calendar week.
        # Shifting the engine's idea of today walks through day 1, 2 and 3 of the split.
        real = date.today()
        for n in range(7):
            fake = real + timedelta(days=n)

            class FakeDate(date):
                @classmethod
                def today(cls, _d=fake):
                    return _d
            with mock.patch.object(engine, 'date', FakeDate):
                page = vp.build_page()
            for key in ('run_a', 'run_b'):
                rows = [r for r in page[key]['rows'] if r['pattern'] == 'lunge' and r['unilateral']]
                self.assertTrue(rows, (n, key))
                self.assertTrue(all(r['sets_weak'] == r['sets'] + (2 if key == 'run_a' else 1)
                                    for r in rows), (n, key))

    # -- constants the page depends on ----------------------------------------
    def test_bands_extra_sets_and_hop_benchmark_are_pinned(self):
        band = lambda w: _compute_asymmetry_raw(w, 100)[0]
        self.assertEqual([band(85), band(84), band(70), band(69), band(55), band(54)],
                         ['none', 'mild', 'mild', 'moderate', 'moderate', 'significant'])
        extra = lambda b: engine._get_exercise_asymmetry('lunge', {'lunge': {'asymmetry': b}})['extra_sets_weak']
        self.assertEqual([extra('none'), extra('mild'), extra('moderate'), extra('significant')],
                         [0, 0, 1, 2])
        self.assertEqual(LSI_THRESHOLDS['hop'], 90)
        self.assertEqual(self.page['hop_bench'], 90)

    def test_lunge_lsi_values_come_from_the_engine_function(self):
        self.assertEqual(self.page['sym']['lunge'], (50.0, 63.6))
        self.assertEqual(self.page['sym']['hop'][1], 87.4)
        self.assertAlmostEqual(self.page['sym']['hop'][0], 78, delta=0.5)
        self.assertEqual(_compute_asymmetry_raw(*vp.LUNGE_EARLIER)[0], 'significant')
        self.assertEqual(_compute_asymmetry_raw(*vp.LUNGE_NOW)[0], 'moderate')

    # -- protocols ------------------------------------------------------------
    def test_now_weak_side_sets_are_sets_plus_one_and_earlier_plus_two(self):
        for key, add in (('run_b', 1), ('run_a', 2)):
            rows = [r for r in self.page[key]['rows'] if r['pattern'] == 'lunge' and r['unilateral']]
            self.assertTrue(rows, key)
            for r in rows:
                self.assertEqual(r['sets_weak'], r['sets'] + add, (key, r))

    def test_earlier_run_blocks_lunge_progression_now_run_does_not(self):
        a, b = self.page['run_a'], self.page['run_b']
        self.assertIn('lunge', a['blocked'])
        self.assertNotIn('lunge', a['advanced'])
        self.assertNotIn('lunge', b['blocked'])

    def test_two_comfortable_sessions_progress_as_check_progression_ready_says(self):
        b = self.page['run_b']
        patterns = {r['pattern'] for r in b['rows']}
        self.assertIn('lunge', patterns)
        for p in patterns:
            if p in b['ready']:
                self.assertEqual(p in b['advanced'], b['ready'][p], p)
        self.assertTrue(b['ready']['lunge'])
        self.assertIn('lunge', b['advanced'])

    def test_advanced_level_is_saved_and_is_saved_for_the_next_session(self):
        # Proves the page wording: this plan keeps level 2, the saved level becomes 3,
        # and the next plan from the same patient uses level 3.
        from django.db import transaction
        now = vp.timezone.now()
        with transaction.atomic():
            try:
                p, _ = vp._persona_now('exhtest1', now, date.today())
                first = vp._protocol(engine.generate_v1_session(p), p)
                saved = StrengthProfile.objects.filter(patient=p).order_by('-assessment_number').first()
                saved_now = saved.lunge_score
                self.assertIn('lunge', first['advanced'])
                self.assertEqual(first['advanced']['lunge'], 3)
                self.assertEqual({r['level'] for r in first['rows'] if r['pattern'] == 'lunge'}, {2})
                self.assertEqual(saved_now, 3)
                # The next plan reads the saved level: every pattern it shows has the
                # level that is saved for it (lunge may be absent: it is only added
                # while it is the weakest pattern).
                latest = lambda: p.strength_profiles.order_by('-assessed_at').first()
                saved = {k: getattr(latest(), k + '_score') for k in
                         ('squat', 'hinge', 'push', 'pull', 'rotate', 'lunge')}
                nxt = vp._protocol(engine.generate_v1_session(p), p)
                self.assertTrue(nxt['rows'])
                for r in nxt['rows']:
                    if r['pattern'] in saved:
                        self.assertEqual(r['level'], saved[r['pattern']], r['pattern'])
                self.assertEqual(saved['lunge'], 3)
            finally:
                transaction.set_rollback(True)

    def test_hand_set_week_equals_the_latest_week_shown_in_the_history(self):
        now = vp.timezone.now()
        from django.db import transaction
        with transaction.atomic():
            try:
                for build in (vp._persona_early, vp._persona_now):
                    p, sess = build('exhtest2', now, date.today())
                    shown = vp.WEEKS - min(s['week_k'] for s in sess)
                    self.assertEqual(p.periodisation.current_week, shown)
            finally:
                transaction.set_rollback(True)
        self.assertEqual(self.page['weeks'][-1]['label'], 'Week %d (latest)' % vp.WEEKS)

    def test_level_wording_says_next_session(self):
        self.assertIn('saved for the next session', vp.TEXT['why_adv'])
        row = next(d for d in self.page['diff'] if d['pattern'] == 'lunge' and d['b'])
        self.assertTrue(any('level 3 saved for the next session' in w for w in row['why']))
        lv = {r['level'] for r in self.page['run_b']['rows'] if r['pattern'] == 'lunge'}
        self.assertEqual(lv, {2})

    def test_no_deload_in_now_and_both_runs_are_plans(self):
        for key in ('run_a', 'run_b'):
            self.assertEqual(self.page[key]['status'], 'ready')
            self.assertFalse(self.page[key]['deload'])
            self.assertEqual(self.page[key]['phase'], 'hypertrophy')

    def test_why_labels_come_from_rule_results(self):
        lunge = [d for d in self.page['diff'] if d['pattern'] == 'lunge']
        self.assertTrue(lunge)
        joined = ' '.join(w for d in lunge for w in d['why'])
        self.assertIn('Symmetry band significant', joined)
        self.assertIn('Symmetry band moderate', joined)
        self.assertIn('Progression blocked', joined)
        self.assertIn('Ready to progress', joined)

    # -- page text ------------------------------------------------------------
    def test_page_text(self):
        html = self.client.get(URL).content.decode().lower()
        text = re.sub(r'<[^>]+>', ' ', html)
        self.assertIn('illustrative demo data', text)
        self.assertIn('returned to training', text)
        self.assertIn('training state set for this demo', text)
        self.assertIn('computed live by the engine', text)
        for word in BANNED:
            self.assertNotIn(word, text)
        # No script of any kind: nothing from the request reaches JS.
        self.assertNotIn('<script', html)

    def test_strings_in_text_dict_are_free_of_banned_words(self):
        blob = ' '.join(str(v) for v in vp.TEXT.values()).lower()
        for word in BANNED:
            self.assertNotIn(word, blob)


def _hero_html(html):
    m = re.search(r'<section class="hero">(.*?)</section>', html, re.S)
    return m.group(1)


def _hero_numbers(html):
    return [re.sub(r'\s+', '', re.sub(r'<[^>]+>|&rarr;', ' ', n))
            for n in re.findall(r'<div class="nums">(.*?)</div>', _hero_html(html), re.S)]


@override_settings(EXHIBITION_MODE=True)
class HeroTests(TestCase):
    def _get(self):
        return self.client.get(URL).content.decode()

    def test_hero_numbers_equal_the_engine_values_of_this_request(self):
        seen = {}
        real = vp.build_page

        def spy():
            seen['page'] = real()
            return seen['page']
        with mock.patch.object(vp, 'build_page', spy):
            html = self._get()
        page = seen['page']
        lunge_a = [r for r in page['run_a']['rows'] if r['pattern'] == 'lunge' and r['unilateral']][0]
        lunge_b = [r for r in page['run_b']['rows'] if r['pattern'] == 'lunge' and r['unilateral']][0]
        expected = [
            '%d%%%d%%' % (round(page['sym']['lunge'][0]), round(page['sym']['lunge'][1])),
            '+%d+%d' % (lunge_a['extra'], lunge_b['extra']),
            '%d%d' % (lunge_a['level'], page['run_b']['advanced']['lunge']),
        ]
        got = [n.replace('nextsession', '') for n in _hero_numbers(html)]
        self.assertEqual(got, expected)
        self.assertEqual(got, ['50%64%', '+2+1', '23'])

    def test_moving_the_lunge_pair_changes_hero_balance_and_extra_sets(self):
        base = _hero_numbers(self._get())
        with mock.patch.object(vp, 'LUNGE_NOW', (6, 12)):
            moved = _hero_numbers(self._get())
        self.assertNotEqual(base[0], moved[0])
        self.assertEqual(moved[0], '50%50%')
        self.assertEqual(moved[1], '+2+2')
        self.assertEqual(base[1], '+2+1')

    def test_hero_has_the_illustrative_label(self):
        self.assertIn('Illustrative demo data', _hero_html(self._get()))

    def test_hero_visible_text_is_at_most_40_words_numbers_not_counted(self):
        text = re.sub(r'<[^>]+>|&rarr;|&darr;', ' ', _hero_html(self._get()))
        words = [w for w in text.split() if not re.search(r'\d', w)]
        self.assertLessEqual(len(words), 40, words)

    def test_missing_values_show_a_dash_and_the_page_renders(self):
        page = vp.build_page()
        empty = {'rows': [], 'advanced': {}}
        self.assertEqual(vp._hero(empty, empty, {'lunge': (None, None)}),
                         {'balance': ('-', '-'), 'extra': ('-', '-'), 'level': ('-', '-')})

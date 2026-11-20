"""Check-In 4, mind_lab_day_mode gating table, visitor mode stores nothing."""

import ast
from pathlib import Path
from unittest import mock

from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from strength_app import v1_mind_lab_visitor_views
from strength_app.mind_lab import checkin as ci
from strength_app.mind_lab import config
from strength_app.mind_lab import day_mode as dm
from strength_app.models import GameSession, MindLabCheckIn
from strength_app.tests.test_mind_lab import make_athlete


class TestGatingTable(SimpleTestCase):
    """One test per row of the workbook's Mind Lab Session sheet."""

    def test_full_day(self):
        self.assertEqual(dm.resolve_day_mode('over_6', 'green'), 'full')

    def test_sleep_5_to_6_shortened(self):
        self.assertEqual(dm.resolve_day_mode('5_to_6', 'green'), 'shortened')

    def test_sleep_under_5_recovery_only(self):
        self.assertEqual(dm.resolve_day_mode('under_5', 'green'), 'recovery_only')

    def test_pain_yellow_shortened(self):
        self.assertEqual(dm.resolve_day_mode('over_6', 'yellow'), 'shortened')

    def test_pain_red_checkin_breath_only(self):
        self.assertEqual(dm.resolve_day_mode('over_6', 'red'), 'checkin_breath_only')

    def test_pain_overrides_sleep(self):
        for sleep in ('under_5', '5_to_6', 'over_6'):
            self.assertEqual(dm.resolve_day_mode(sleep, 'red'), 'checkin_breath_only')

    def test_worst_state_wins(self):
        self.assertEqual(dm.resolve_day_mode('under_5', 'yellow'), 'recovery_only')
        self.assertEqual(dm.resolve_day_mode('5_to_6', 'yellow'), 'shortened')

    def test_no_checkin_yet_is_checkin_only(self):
        self.assertEqual(dm.resolve_day_mode(None, 'green'), 'checkin_breath_only')

    def test_hold_returns_checkin_breath_only(self):
        self.assertEqual(dm.resolve_day_mode('over_6', 'green', hold=True),
                         'checkin_breath_only')

    def test_s3_hook_has_no_source_yet(self):
        self.assertFalse(dm.s3_hold_active(object()))

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            dm.resolve_day_mode('over_6', 'purple')
        with self.assertRaises(ValueError):
            dm.resolve_day_mode('9h', 'green')


class TestCheckinLogic(SimpleTestCase):
    def test_score_range(self):
        self.assertEqual(ci.checkin_score(5, 1, 1), 3)
        self.assertEqual(ci.checkin_score(1, 5, 5), 15)

    def test_labels_err_toward_light_or_recovery(self):
        self.assertEqual(ci.score_label(config.CHECKIN_FULL_MIN_SCORE), 'full')
        self.assertEqual(ci.score_label(config.CHECKIN_FULL_MIN_SCORE - 1), 'light')
        self.assertEqual(ci.score_label(config.CHECKIN_LIGHT_MIN_SCORE), 'light')
        self.assertEqual(ci.score_label(config.CHECKIN_LIGHT_MIN_SCORE - 1), 'recovery')
        self.assertGreater(config.CHECKIN_FULL_MIN_SCORE, 9)  # above the scale midpoint

    def test_worse_of_score_and_mode(self):
        self.assertEqual(ci.day_label(15, 'recovery_only'), 'recovery')
        self.assertEqual(ci.day_label(15, 'shortened'), 'light')
        self.assertEqual(ci.day_label(3, 'full'), 'recovery')

    def test_clean_answers_rejects_bad(self):
        for bad in (('x', 3, 3, 3), ('over_6', 0, 3, 3), ('over_6', 3, 6, 3),
                    ('over_6', 3, 3, 'a'), ('over_6', True, 3, 3), ('over_6', 3, 3, None)):
            with self.assertRaises(ValueError, msg=bad):
                ci.clean_answers(*bad)

    def test_support_line_trigger(self):
        self.assertTrue(ci.show_support_line(3, 1))
        self.assertTrue(ci.show_support_line(1, 3))
        self.assertFalse(ci.show_support_line(3, 3))


class TestDayModeFromDb(TestCase):
    def setUp(self):
        self.athlete, _ = make_athlete('CIATH1')

    def test_no_feedback_is_green_and_no_checkin_is_checkin_only(self):
        self.assertEqual(dm.pain_light_for(self.athlete), 'green')
        self.assertEqual(dm.mind_lab_day_mode(self.athlete), 'checkin_breath_only')

    def test_todays_checkin_drives_mode(self):
        MindLabCheckIn.objects.create(
            athlete=self.athlete, sleep_bucket='over_6', stress=2, energy=4,
            focus=4, pain_light='green', gate_applied='full', day_label='full')
        self.assertEqual(dm.mind_lab_day_mode(self.athlete), 'full')
        with mock.patch.object(dm, 'pain_light_for', return_value='red'):
            self.assertEqual(dm.mind_lab_day_mode(self.athlete), 'checkin_breath_only')


@override_settings(MIND_LAB_ENABLED=True)
class TestCheckinView(TestCase):
    def setUp(self):
        self.athlete, _ = make_athlete('CIATH2')
        s = self.client.session
        s['patient_id'] = self.athlete.patient_id
        s.save()
        self.url = reverse('mind_lab_checkin')

    def answers(self, **kw):
        base = {'sleep': 'over_6', 'stress': 2, 'energy': 5, 'focus': 5}
        base.update(kw)
        return base

    def test_get_renders_four_questions(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        for name in ('sleep', 'stress', 'energy', 'focus'):
            self.assertContains(resp, f'name="{name}"')

    def test_post_stores_row_and_shows_label(self):
        resp = self.client.post(self.url, self.answers())
        self.assertContains(resp, 'Full day')
        row = MindLabCheckIn.objects.get()
        self.assertEqual((row.gate_applied, row.day_label, row.pain_light),
                         ('full', 'full', 'green'))
        self.assertEqual(GameSession.objects.count(), 0)

    def test_short_sleep_gives_recovery(self):
        resp = self.client.post(self.url, self.answers(sleep='under_5'))
        self.assertContains(resp, 'Recovery-only day')
        self.assertEqual(MindLabCheckIn.objects.get().gate_applied, 'recovery_only')

    def test_red_pain_overrides_good_sleep(self):
        with mock.patch('strength_app.v1_mind_lab_checkin_views.pain_light_for',
                        return_value='red'):
            self.client.post(self.url, self.answers())
        self.assertEqual(MindLabCheckIn.objects.get().gate_applied, 'checkin_breath_only')

    def test_bad_answers_400_and_nothing_stored(self):
        resp = self.client.post(self.url, self.answers(energy=9))
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(MindLabCheckIn.objects.count(), 0)

    def test_support_line_is_the_workbook_line(self):
        resp = self.client.post(self.url, self.answers(energy=1))
        self.assertContains(resp, ci.SUPPORT_LINE)

    def test_signed_out_redirects(self):
        s = self.client.session
        s.flush()
        self.assertEqual(self.client.get(self.url).status_code, 302)


class TestFlagOff(TestCase):
    def test_default_flags_are_false(self):
        from django.conf import settings
        self.assertFalse(settings.MIND_LAB_ENABLED)
        self.assertFalse(settings.RTP_ENABLED)

    def test_both_urls_404_when_off(self):
        for name in ('mind_lab_checkin', 'mind_lab_visitor'):
            self.assertEqual(self.client.get(reverse(name)).status_code, 404)
            self.assertEqual(self.client.post(reverse(name), {}).status_code, 404)


@override_settings(MIND_LAB_ENABLED=True)
class TestVisitorStoresNothing(TestCase):
    url_name = 'mind_lab_visitor'

    def test_full_visitor_run_writes_nothing(self):
        url = reverse(self.url_name)
        self.assertEqual(self.client.get(url).status_code, 200)
        for sleep, energy in (('over_6', 4), ('5_to_6', 3), ('under_5', 1)):
            resp = self.client.post(url, {'sleep': sleep, 'energy': energy})
            self.assertContains(resp, 'Nothing was saved.')
        self.assertEqual(self.client.post(url, {'sleep': 'x', 'energy': 3}).status_code, 400)
        self.assertEqual(MindLabCheckIn.objects.count(), 0)
        self.assertEqual(GameSession.objects.count(), 0)
        self.assertNotIn('sessionid', self.client.cookies)

    def test_visitor_result_and_support_line(self):
        resp = self.client.post(reverse(self.url_name), {'sleep': 'under_5', 'energy': 1})
        self.assertContains(resp, 'Recovery-only day')
        self.assertContains(resp, ci.SUPPORT_LINE)

    def test_visitor_module_has_no_write_path(self):
        """Structural: no models import, no session use, no write call."""
        tree = ast.parse(Path(v1_mind_lab_visitor_views.__file__).read_text())
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

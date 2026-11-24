"""Boundaries of every PAWAN_SETS constant in mind_lab/adaptive.py."""

import math
from unittest import TestCase

from strength_app.mind_lab import adaptive as a


class TestNextLevel(TestCase):
    mid = (a.MIN_LEVEL + a.MAX_LEVEL) // 2
    enough = a.MIN_TRIALS_TO_ADAPT

    def test_constants_are_coherent(self):
        self.assertLess(a.LEVEL_DOWN_ACCURACY, a.LEVEL_UP_ACCURACY)
        self.assertLess(a.MIN_LEVEL, a.MAX_LEVEL)
        self.assertGreater(a.LEVEL_STEP, 0)
        self.assertGreaterEqual(a.MIN_TRIALS_TO_ADAPT, 1)

    # LEVEL_UP_ACCURACY: at the edge moves up, just below holds.
    def test_up_threshold_edges(self):
        up = a.LEVEL_UP_ACCURACY
        self.assertEqual(a.next_level(self.mid, up, self.enough), self.mid + a.LEVEL_STEP)
        self.assertEqual(a.next_level(self.mid, math.nextafter(up, 0), self.enough), self.mid)
        self.assertEqual(a.next_level(self.mid, 1.0, self.enough), self.mid + a.LEVEL_STEP)

    # LEVEL_DOWN_ACCURACY: at the edge holds, just below moves down.
    def test_down_threshold_edges(self):
        down = a.LEVEL_DOWN_ACCURACY
        self.assertEqual(a.next_level(self.mid, down, self.enough), self.mid)
        self.assertEqual(a.next_level(self.mid, math.nextafter(down, 0), self.enough), self.mid - a.LEVEL_STEP)
        self.assertEqual(a.next_level(self.mid, math.nextafter(down, 1), self.enough), self.mid)
        self.assertEqual(a.next_level(self.mid, 0.0, self.enough), self.mid - a.LEVEL_STEP)

    # MIN_TRIALS_TO_ADAPT: one below holds even on perfect/awful scores.
    def test_min_trials_edges(self):
        few = a.MIN_TRIALS_TO_ADAPT - 1
        self.assertEqual(a.next_level(self.mid, 1.0, few), self.mid)
        self.assertEqual(a.next_level(self.mid, 0.0, few), self.mid)
        self.assertEqual(a.next_level(self.mid, 1.0, a.MIN_TRIALS_TO_ADAPT), self.mid + a.LEVEL_STEP)
        self.assertEqual(a.next_level(self.mid, 0.0, a.MIN_TRIALS_TO_ADAPT), self.mid - a.LEVEL_STEP)
        self.assertEqual(a.next_level(self.mid, 1.0, 0), self.mid)

    # MIN_LEVEL / MAX_LEVEL: both sides of each edge.
    def test_level_bounds(self):
        top, bottom = a.MAX_LEVEL, a.MIN_LEVEL
        self.assertEqual(a.next_level(top, 1.0, self.enough), top)
        self.assertEqual(a.next_level(top - a.LEVEL_STEP, 1.0, self.enough), top)
        self.assertEqual(a.next_level(bottom, 0.0, self.enough), bottom)
        self.assertEqual(a.next_level(bottom + a.LEVEL_STEP, 0.0, self.enough), bottom)

    def test_out_of_range_level_is_clamped(self):
        self.assertEqual(a.next_level(a.MAX_LEVEL + 5, 0.7, self.enough), a.MAX_LEVEL)
        self.assertEqual(a.next_level(a.MIN_LEVEL - 5, 0.7, self.enough), a.MIN_LEVEL)

    def test_holds_in_the_middle_band(self):
        mid_acc = (a.LEVEL_UP_ACCURACY + a.LEVEL_DOWN_ACCURACY) / 2
        self.assertEqual(a.next_level(self.mid, mid_acc, self.enough), self.mid)

    def test_unknown_accuracy_holds(self):
        self.assertEqual(a.next_level(self.mid, None, self.enough), self.mid)

    def test_invalid_input_raises(self):
        for acc in (-0.001, 1.001):
            with self.assertRaises(ValueError):
                a.next_level(self.mid, acc, self.enough)
        with self.assertRaises(ValueError):
            a.next_level(self.mid, 0.7, -1)

    def test_module_has_no_django_import(self):
        import inspect
        src = inspect.getsource(a)
        self.assertNotIn('import django', src)
        self.assertNotIn('from django', src)

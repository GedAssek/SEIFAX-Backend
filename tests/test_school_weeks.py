import unittest

from datetime import date

from utils.school_weeks import school_week, selected_date_from_value


class SchoolWeekTests(unittest.TestCase):
    def test_rentree_2026_is_school_week_one(self):
        week = school_week("2026-W41", date(2026, 10, 5))
        self.assertEqual(week["semaine"], "Semaine 01, 2026-2027")
        self.assertEqual(week["date_debut"], "2026-10-05")
        self.assertEqual(week["date_fin"], "2026-10-11")

    def test_a_non_monday_rentree_starts_week_one_on_its_exact_date(self):
        week = school_week("2027-10-08", date(2027, 10, 6))
        self.assertEqual(week["semaine_numero"], 1)
        self.assertEqual(week["date_debut"], "2027-10-06")

    def test_an_iso_date_is_accepted(self):
        self.assertEqual(selected_date_from_value("2026-10-08").isoformat(), "2026-10-08")


if __name__ == "__main__":
    unittest.main()

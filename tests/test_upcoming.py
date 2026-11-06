from datetime import date, timedelta

import pytest

from core.overdue import VaccinationRecord, latest_records, overdue_vaccinations
from core.upcoming import UpcomingItem, is_upcoming, upcoming_revaccinations
from core.vaccination_schedule import UnknownVaccineError

TODAY = date(2026, 11, 6)


def _vaccinated_for_due(due: date, interval: int = 365) -> date:
    return due - timedelta(days=interval)


@pytest.mark.parametrize(
    ("due", "expected"),
    [
        (TODAY - timedelta(days=1), False),
        (TODAY, True),
        (TODAY + timedelta(days=7), True),
        (TODAY + timedelta(days=8), False),
    ],
)
def test_is_upcoming_window_boundaries_are_closed(due, expected):
    assert is_upcoming(due, TODAY, 7) is expected


def test_is_upcoming_negative_days_raises():
    with pytest.raises(ValueError):
        is_upcoming(TODAY, TODAY, -1)


def test_is_upcoming_huge_days_does_not_overflow():
    assert is_upcoming(date(9999, 12, 31), TODAY, 10**9) is True


def test_upcoming_revaccinations_returns_only_records_in_window():
    records = [
        VaccinationRecord(1, "Сказ", _vaccinated_for_due(TODAY + timedelta(days=3))),
        VaccinationRecord(2, "Сказ", _vaccinated_for_due(TODAY + timedelta(days=30))),
    ]
    assert upcoming_revaccinations(records, TODAY, 7) == [
        UpcomingItem(1, "Сказ", TODAY + timedelta(days=3), 3)
    ]


def test_upcoming_revaccinations_due_today_included_and_overdue_excluded():
    records = [
        VaccinationRecord(1, "Сказ", _vaccinated_for_due(TODAY)),
        VaccinationRecord(2, "Сказ", _vaccinated_for_due(TODAY - timedelta(days=1))),
    ]
    assert upcoming_revaccinations(records, TODAY, 7) == [UpcomingItem(1, "Сказ", TODAY, 0)]


def test_upcoming_revaccinations_days_zero_returns_only_today():
    records = [
        VaccinationRecord(1, "Сказ", _vaccinated_for_due(TODAY)),
        VaccinationRecord(2, "Сказ", _vaccinated_for_due(TODAY + timedelta(days=1))),
    ]
    assert upcoming_revaccinations(records, TODAY, 0) == [UpcomingItem(1, "Сказ", TODAY, 0)]


def test_upcoming_revaccinations_negative_days_raises():
    with pytest.raises(ValueError):
        upcoming_revaccinations([], TODAY, -1)


def test_upcoming_revaccinations_newer_record_outside_window_cancels_old_one():
    records = [
        VaccinationRecord(1, "Сказ", _vaccinated_for_due(TODAY + timedelta(days=2))),  # у вікні
        VaccinationRecord(1, "Сказ", TODAY - timedelta(days=10)),  # свіжіша, due далеко
    ]
    assert upcoming_revaccinations(records, TODAY, 7) == []


def test_upcoming_revaccinations_newer_record_in_window_is_used_instead_of_old():
    newer = _vaccinated_for_due(TODAY + timedelta(days=5))
    records = [
        VaccinationRecord(1, "Сказ", newer - timedelta(days=400)),  # стара, due давно минув
        VaccinationRecord(1, "Сказ", newer),
    ]
    assert upcoming_revaccinations(records, TODAY, 7) == [
        UpcomingItem(1, "Сказ", TODAY + timedelta(days=5), 5)
    ]


def test_upcoming_revaccinations_different_vaccines_of_one_animal_are_independent():
    records = [
        VaccinationRecord(1, "Сказ", _vaccinated_for_due(TODAY + timedelta(days=4), 365)),
        VaccinationRecord(1, "Бордетела", _vaccinated_for_due(TODAY + timedelta(days=2), 180)),
    ]
    assert upcoming_revaccinations(records, TODAY, 7) == [
        UpcomingItem(1, "Бордетела", TODAY + timedelta(days=2), 2),
        UpcomingItem(1, "Сказ", TODAY + timedelta(days=4), 4),
    ]


def test_upcoming_revaccinations_sorted_by_due_then_animal_then_vaccine():
    due = TODAY + timedelta(days=3)
    records = [
        VaccinationRecord(2, "Сказ", _vaccinated_for_due(due)),
        VaccinationRecord(1, "Сказ", _vaccinated_for_due(due)),
        VaccinationRecord(1, "DHPPi", _vaccinated_for_due(due)),
        VaccinationRecord(3, "Сказ", _vaccinated_for_due(TODAY + timedelta(days=1))),
    ]
    result = [(i.animal_id, i.vaccine) for i in upcoming_revaccinations(records, TODAY, 7)]
    assert result == [(3, "Сказ"), (1, "DHPPi"), (1, "Сказ"), (2, "Сказ")]


def test_upcoming_revaccinations_unknown_vaccine_raises():
    with pytest.raises(UnknownVaccineError):
        upcoming_revaccinations([VaccinationRecord(1, "Невідома", TODAY)], TODAY, 7)


def test_upcoming_revaccinations_leap_day_uses_days_not_calendar_year():
    records = [VaccinationRecord(1, "Сказ", date(2024, 2, 29))]  # due 2025-02-28
    today = date(2025, 2, 25)
    assert upcoming_revaccinations(records, today, 3) == [UpcomingItem(1, "Сказ", date(2025, 2, 28), 3)]
    assert upcoming_revaccinations(records, today, 2) == []


def test_upcoming_revaccinations_empty_input():
    assert upcoming_revaccinations([], TODAY, 7) == []


def test_upcoming_revaccinations_huge_days_returns_all_future_records():
    records = [
        VaccinationRecord(1, "Сказ", _vaccinated_for_due(TODAY + timedelta(days=1))),
        VaccinationRecord(2, "Сказ", _vaccinated_for_due(TODAY + timedelta(days=1000))),
        VaccinationRecord(3, "Сказ", _vaccinated_for_due(TODAY - timedelta(days=1))),
    ]
    assert [i.animal_id for i in upcoming_revaccinations(records, TODAY, 10**9)] == [1, 2]


def test_upcoming_and_overdue_do_not_overlap_and_cover_all_due_dates():
    records = [
        VaccinationRecord(i, "Сказ", _vaccinated_for_due(TODAY + timedelta(days=d)))
        for i, d in enumerate([-2, -1, 0, 1, 5], start=1)
    ]
    overdue_ids = {i.animal_id for i in overdue_vaccinations(records, TODAY)}
    upcoming_ids = {i.animal_id for i in upcoming_revaccinations(records, TODAY, 10**6)}
    assert overdue_ids.isdisjoint(upcoming_ids)
    assert overdue_ids | upcoming_ids == {1, 2, 3, 4, 5}


def test_latest_records_keeps_newest_per_animal_and_vaccine():
    old = VaccinationRecord(1, "Сказ", date(2024, 1, 1))
    new = VaccinationRecord(1, "Сказ", date(2026, 5, 1))
    other = VaccinationRecord(1, "Бордетела", date(2025, 1, 1))
    assert sorted(latest_records([old, new, other]), key=lambda r: r.vaccine) == [other, new]


def test_latest_records_empty_input():
    assert latest_records([]) == []

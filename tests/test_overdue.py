from datetime import date

import pytest

from core.overdue import OverdueItem, VaccinationRecord, is_overdue, overdue_vaccinations

TODAY = date(2026, 11, 6)


@pytest.mark.parametrize(
    ("due", "expected"),
    [(date(2026, 11, 5), True), (date(2026, 11, 6), False), (date(2026, 11, 7), False)],
)
def test_is_overdue_boundary_is_strict(due, expected):
    assert is_overdue(due, TODAY) is expected


def test_overdue_vaccinations_returns_only_overdue():
    records = [
        VaccinationRecord(1, "Сказ", date(2025, 1, 1)),  # due 2026-01-01 -> прострочена
        VaccinationRecord(2, "Сказ", date(2026, 6, 1)),  # due 2027-06-01 -> ні
    ]
    assert overdue_vaccinations(records, TODAY) == [OverdueItem(1, "Сказ", date(2026, 1, 1), 309)]


def test_overdue_vaccinations_uses_latest_record_per_animal_and_vaccine():
    records = [
        VaccinationRecord(1, "Сказ", date(2024, 1, 1)),
        VaccinationRecord(1, "Сказ", date(2026, 5, 1)),  # свіжіша вакцинація знімає прострочення
    ]
    assert overdue_vaccinations(records, TODAY) == []


def test_overdue_vaccinations_sorted_by_days_overdue_desc():
    records = [
        VaccinationRecord(2, "Сказ", date(2025, 6, 1)),
        VaccinationRecord(1, "Сказ", date(2025, 1, 1)),
    ]
    assert [i.animal_id for i in overdue_vaccinations(records, TODAY)] == [1, 2]


def test_overdue_vaccinations_empty_input():
    assert overdue_vaccinations([], TODAY) == []

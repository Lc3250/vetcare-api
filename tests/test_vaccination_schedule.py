from datetime import date

import pytest

from core.vaccination_schedule import UnknownVaccineError, Vaccine, get_vaccine, next_due_date


@pytest.mark.parametrize(
    ("vaccinated_on", "vaccine", "expected"),
    [
        (date(2026, 1, 10), "Сказ", date(2027, 1, 10)),
        (date(2026, 1, 10), "Бордетела", date(2026, 7, 9)),
        (date(2025, 12, 31), "FVRCP", date(2026, 12, 31)),
    ],
)
def test_next_due_date_adds_interval_in_days(vaccinated_on, vaccine, expected):
    assert next_due_date(vaccinated_on, vaccine) == expected


def test_next_due_date_leap_day_uses_days_not_calendar_year():
    # ADR-003: інтервал у днях, тому 29.02.2024 + 365 днів = 28.02.2025
    assert next_due_date(date(2024, 2, 29), "Сказ") == date(2025, 2, 28)


def test_next_due_date_accepts_vaccine_object():
    custom = Vaccine("Тест", "dog", 10)
    assert next_due_date(date(2026, 1, 1), custom) == date(2026, 1, 11)


def test_get_vaccine_returns_reference_entry():
    v = get_vaccine("Сказ")
    assert v.species == "dog" and v.interval_days == 365


def test_unknown_vaccine_raises():
    with pytest.raises(UnknownVaccineError):
        next_due_date(date(2026, 1, 1), "Невідома")

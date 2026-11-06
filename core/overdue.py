"""Список прострочених ревакцинацій (ФВ-6)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from core.vaccination_schedule import next_due_date


@dataclass(frozen=True)
class VaccinationRecord:
    animal_id: int
    vaccine: str
    vaccinated_on: date


@dataclass(frozen=True)
class OverdueItem:
    animal_id: int
    vaccine: str
    due_on: date
    days_overdue: int


def is_overdue(due_on: date, today: date) -> bool:
    """Вакцинація прострочена, якщо дата ревакцинації вже минула (строго раніше сьогодні)."""
    return due_on < today


def latest_records(records: list[VaccinationRecord]) -> list[VaccinationRecord]:
    """Для кожної пари (тварина, вакцина) залишає лише останню вакцинацію (ADR-008)."""
    latest: dict[tuple[int, str], VaccinationRecord] = {}
    for r in records:
        key = (r.animal_id, r.vaccine)
        if key not in latest or r.vaccinated_on > latest[key].vaccinated_on:
            latest[key] = r
    return list(latest.values())


def overdue_vaccinations(records: list[VaccinationRecord], today: date) -> list[OverdueItem]:
    """Для кожної пари (тварина, вакцина) бере останню вакцинацію й повертає прострочені."""
    items = []
    for r in latest_records(records):
        due = next_due_date(r.vaccinated_on, r.vaccine)
        if is_overdue(due, today):
            items.append(OverdueItem(r.animal_id, r.vaccine, due, (today - due).days))
    return sorted(items, key=lambda i: (-i.days_overdue, i.animal_id, i.vaccine))

"""Нагадування про ревакцинацію в найближчі N днів."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from core.overdue import VaccinationRecord, latest_records
from core.vaccination_schedule import next_due_date


@dataclass(frozen=True)
class UpcomingItem:
    animal_id: int
    vaccine: str
    due_on: date
    days_left: int  # 0 = ревакцинація сьогодні


def is_upcoming(due_on: date, today: date, days: int) -> bool:
    """Ревакцинація в найближчі `days` днів: вікно закрите з обох боків, `0 <= due_on - today <= days`.

    Прострочені (due_on < today) сюди не входять, це сфера core.overdue (ADR-008).
    Різниця дат порівнюється, а не `today + timedelta(days)`, щоб великий `days` не давав OverflowError.
    """
    if days < 0:
        raise ValueError("days не може бути від'ємним")
    return 0 <= (due_on - today).days <= days


def upcoming_revaccinations(records: list[VaccinationRecord], today: date, days: int) -> list[UpcomingItem]:
    """Для кожної пари (тварина, вакцина) бере останню вакцинацію й повертає ті, ревакцинація яких у вікні."""
    if days < 0:
        raise ValueError("days не може бути від'ємним")
    items = []
    for r in latest_records(records):
        due = next_due_date(r.vaccinated_on, r.vaccine)
        if is_upcoming(due, today, days):
            items.append(UpcomingItem(r.animal_id, r.vaccine, due, (due - today).days))
    return sorted(items, key=lambda i: (i.due_on, i.animal_id, i.vaccine))

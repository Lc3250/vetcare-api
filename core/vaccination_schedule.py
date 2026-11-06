"""Розрахунок дати наступної ревакцинації (ФВ-5)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta


class UnknownVaccineError(KeyError):
    """Вакцини немає в довіднику."""


@dataclass(frozen=True)
class Vaccine:
    name: str
    species: str
    interval_days: int


# Навчальний довідник, не клінічна рекомендація (ADR-003: інтервал у днях).
VACCINES: dict[str, Vaccine] = {
    v.name: v
    for v in (
        Vaccine("Сказ", "dog", 365),
        Vaccine("DHPPi", "dog", 365),
        Vaccine("Лептоспіроз", "dog", 365),
        Vaccine("Бордетела", "dog", 180),
        Vaccine("FVRCP", "cat", 365),
        Vaccine("FeLV", "cat", 365),
    )
}


def get_vaccine(name: str) -> Vaccine:
    try:
        return VACCINES[name]
    except KeyError:
        raise UnknownVaccineError(name) from None


def next_due_date(vaccinated_on: date, vaccine: Vaccine | str) -> date:
    """Дата ревакцинації = дата вакцинації + інтервал вакцини в днях."""
    v = get_vaccine(vaccine) if isinstance(vaccine, str) else vaccine
    return vaccinated_on + timedelta(days=v.interval_days)

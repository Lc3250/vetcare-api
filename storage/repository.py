"""Доступ до SQLite (ADR-001): лише параметризовані запити."""
from __future__ import annotations

import sqlite3
from datetime import date

from core.overdue import VaccinationRecord

SCHEMA = """
CREATE TABLE IF NOT EXISTS owners (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    phone TEXT
);
CREATE TABLE IF NOT EXISTS animals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id INTEGER NOT NULL REFERENCES owners(id),
    species TEXT NOT NULL,
    name TEXT NOT NULL,
    birth_date TEXT
);
CREATE TABLE IF NOT EXISTS vaccinations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    animal_id INTEGER NOT NULL REFERENCES animals(id),
    vaccine TEXT NOT NULL,
    vaccinated_on TEXT NOT NULL,
    batch TEXT
);
"""


class Repository:
    def __init__(self, path: str = ":memory:"):
        self.conn = sqlite3.connect(path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        # LIKE у SQLite не ігнорує регістр для кирилиці, тому порівнюємо згорнуті рядки
        self.conn.create_function("py_fold", 1, lambda s: s.casefold() if isinstance(s, str) else s, deterministic=True)
        self.conn.executescript(SCHEMA)

    def add_owner(self, full_name: str, phone: str | None = None) -> int:
        cur = self.conn.execute("INSERT INTO owners (full_name, phone) VALUES (?, ?)", (full_name, phone))
        self.conn.commit()
        return cur.lastrowid

    def add_animal(self, owner_id: int, species: str, name: str, birth_date: date | None = None) -> int:
        cur = self.conn.execute(
            "INSERT INTO animals (owner_id, species, name, birth_date) VALUES (?, ?, ?, ?)",
            (owner_id, species, name, birth_date.isoformat() if birth_date else None),
        )
        self.conn.commit()
        return cur.lastrowid

    def add_vaccination(self, animal_id: int, vaccine: str, vaccinated_on: date, batch: str | None = None) -> int:
        cur = self.conn.execute(
            "INSERT INTO vaccinations (animal_id, vaccine, vaccinated_on, batch) VALUES (?, ?, ?, ?)",
            (animal_id, vaccine, vaccinated_on.isoformat(), batch),
        )
        self.conn.commit()
        return cur.lastrowid

    def find_animals(self, name: str) -> list[dict]:
        escaped = name.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_").casefold()
        rows = self.conn.execute(
            "SELECT id, owner_id, species, name FROM animals WHERE py_fold(name) LIKE ? ESCAPE '\\' ORDER BY id",
            (f"%{escaped}%",),
        ).fetchall()
        return [dict(zip(("id", "owner_id", "species", "name"), r, strict=True)) for r in rows]

    def vaccination_records(self) -> list[VaccinationRecord]:
        rows = self.conn.execute("SELECT animal_id, vaccine, vaccinated_on FROM vaccinations").fetchall()
        return [VaccinationRecord(a, v, date.fromisoformat(d)) for a, v, d in rows]

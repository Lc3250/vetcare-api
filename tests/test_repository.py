from datetime import date

import pytest

from core.overdue import VaccinationRecord
from storage.repository import Repository


@pytest.fixture
def repo():
    return Repository(":memory:")


def test_add_and_find_animal(repo):
    owner = repo.add_owner("Тест Власник", "+380000000000")
    animal = repo.add_animal(owner, "dog", "Барсик", date(2020, 5, 1))
    assert repo.find_animals("барс") == [{"id": animal, "owner_id": owner, "species": "dog", "name": "Барсик"}]


def test_vaccination_records_roundtrip_dates(repo):
    owner = repo.add_owner("Власник")
    animal = repo.add_animal(owner, "cat", "Мурка")
    repo.add_vaccination(animal, "FVRCP", date(2026, 3, 1), batch="A1")
    assert repo.vaccination_records() == [VaccinationRecord(animal, "FVRCP", date(2026, 3, 1))]


def test_foreign_key_rejects_animal_without_owner(repo):
    import sqlite3

    with pytest.raises(sqlite3.IntegrityError):
        repo.add_animal(999, "dog", "Привид")


def test_queries_are_parameterized(repo):
    owner = repo.add_owner("Власник")
    repo.add_animal(owner, "dog", "Рекс")
    # SQL-ін'єкція в пошуку має сприйматися як звичайний текст
    assert repo.find_animals("x'; DROP TABLE animals; --") == []
    assert len(repo.find_animals("Рекс")) == 1


def test_find_animals_treats_wildcards_literally(repo):
    owner = repo.add_owner("Власник")
    repo.add_animal(owner, "dog", "Рекс")
    assert repo.find_animals("%") == []
    assert repo.find_animals("_екс") == []

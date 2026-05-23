from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from app.config import settings

Sex = Literal["male", "female"]
LifeStage = Literal["puppy", "adolescent", "adult", "senior"]


def _today_utc() -> date:
    return datetime.now(UTC).date()


def _weeks_between(start: date, end: date) -> int:
    return max(0, (end - start).days // 7)


def _years_between(start: date, end: date) -> int:
    years = end.year - start.year
    if (end.month, end.day) < (start.month, start.day):
        years -= 1
    return max(0, years)


def _months_remainder(start: date, end: date, full_years: int) -> int:
    anchor_year = start.year + full_years
    anchor = date(anchor_year, start.month, min(start.day, 28))
    months = end.month - anchor.month
    if end.day < anchor.day:
        months -= 1
    if months < 0:
        months += 12
    return max(0, months)


def _life_stage_from_age(years: int, months: int) -> LifeStage:
    if years == 0 and months < 12:
        return "puppy"
    if years < 2:
        return "adolescent"
    if years < 8:
        return "adult"
    return "senior"


MAX_BIRTHDAY_AGE_YEARS = 22


def _validate_birthday(value: date) -> date:
    today = _today_utc()
    if value > today:
        raise ValueError("birthday must be in the past")
    earliest = date(today.year - MAX_BIRTHDAY_AGE_YEARS, today.month, today.day)
    if value < earliest:
        raise ValueError(f"birthday cannot be more than {MAX_BIRTHDAY_AGE_YEARS} years ago")
    return value


class PetBase(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    breed_other: str | None = Field(default=None, max_length=80)
    birthday: date
    sex: Sex
    spayed_neutered: bool
    weight_grams: int = Field(ge=100, le=120000)
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("birthday")
    @classmethod
    def _birthday_must_be_past_and_not_ancient(cls, value: date) -> date:
        return _validate_birthday(value)


class PetCreate(PetBase):
    pass


class PetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=60)
    breed_other: str | None = Field(default=None, max_length=80)
    birthday: date | None = None
    sex: Sex | None = None
    spayed_neutered: bool | None = None
    weight_grams: int | None = Field(default=None, ge=100, le=120000)
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("birthday")
    @classmethod
    def _birthday_must_be_past_and_not_ancient(cls, value: date | None) -> date | None:
        if value is None:
            return value
        return _validate_birthday(value)


class PetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    breed_other: str | None
    birthday: date
    sex: Sex
    spayed_neutered: bool
    weight_grams: int
    notes: str | None
    photo_path: str | None
    created_at: datetime
    updated_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def age_years(self) -> int:
        return _years_between(self.birthday, _today_utc())

    @computed_field  # type: ignore[prop-decorator]
    @property
    def age_months(self) -> int:
        today = _today_utc()
        years = _years_between(self.birthday, today)
        return _months_remainder(self.birthday, today, years)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def age_weeks(self) -> int:
        return _weeks_between(self.birthday, _today_utc())

    @computed_field  # type: ignore[prop-decorator]
    @property
    def life_stage(self) -> LifeStage:
        return _life_stage_from_age(self.age_years, self.age_months)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def photo_url(self) -> str | None:
        if self.photo_path is None:
            return None
        return f"{settings.backend_base_url.rstrip('/')}/media/{self.photo_path}"

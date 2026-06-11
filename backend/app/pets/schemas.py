from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Literal

from dateutil.relativedelta import relativedelta
from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from app.config import settings

Sex = Literal["male", "female"]
LifeStage = Literal["puppy", "adolescent", "adult", "senior"]


def _today_utc() -> date:
    return datetime.now(UTC).date()


def _age_delta(birthday: date, today: date) -> relativedelta:
    return relativedelta(today, birthday)


def _weeks_between(start: date, end: date) -> int:
    return max(0, (end - start).days // 7)


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

    earliest = today - relativedelta(years=MAX_BIRTHDAY_AGE_YEARS)
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

    @field_validator(
        "name",
        "birthday",
        "sex",
        "spayed_neutered",
        "weight_grams",
        mode="before",
    )
    @classmethod
    def _reject_explicit_null(cls, value: object) -> object:
        if value is None:
            raise ValueError("cannot be null — omit the field to leave it unchanged")
        return value

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
        return max(0, int(_age_delta(self.birthday, _today_utc()).years))

    @computed_field  # type: ignore[prop-decorator]
    @property
    def age_months(self) -> int:
        return max(0, int(_age_delta(self.birthday, _today_utc()).months))

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
        base = settings.backend_base_url.rstrip("/")
        # Authenticated, owner-scoped route (see GET /pets/{id}/photo). The
        # filename stem (a per-upload uuid) doubles as a cache-buster so a
        # replaced photo gets a fresh URL despite the stable route path.
        version = self.photo_path.rsplit("/", 1)[-1].split(".", 1)[0]
        return f"{base}/pets/{self.id}/photo?v={version}"

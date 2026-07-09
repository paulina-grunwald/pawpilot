from __future__ import annotations

import base64
import binascii
import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    field_validator,
    model_validator,
)

from app.config import settings

MealCategory = Literal["kibble", "wet", "home_cooked", "treat"]
BathroomKind = Literal["poop", "pee", "both"]
BathroomColor = Literal["brown", "dark", "mustard", "orange", "black", "red"]
BodyArea = Literal[
    "mouth",
    "nose",
    "eyes",
    "ears",
    "head",
    "neck",
    "chest",
    "back",
    "skin",
    "belly",
    "hind",
    "tail",
    "paws",
]
WeightSource = Literal["home_scale", "vet"]

MAX_TAGS = 20


class MealPayload(BaseModel):
    entry_type: Literal["meal"] = "meal"
    food_name: str = Field(min_length=1, max_length=200)
    brand: str | None = Field(default=None, max_length=200)
    amount_grams: int | None = Field(default=None, gt=0)
    category: MealCategory


class BathroomPayload(BaseModel):
    entry_type: Literal["bathroom"] = "bathroom"
    kind: BathroomKind
    bristol_score: int | None = Field(default=None, ge=1, le=7)
    color: BathroomColor | None = None

    @model_validator(mode="after")
    def _pee_has_no_stool_fields(self) -> BathroomPayload:
        if self.kind == "pee" and (self.bristol_score is not None or self.color is not None):
            raise ValueError("bristol_score and color are only allowed when kind includes poop")
        return self


class SymptomPayload(BaseModel):
    entry_type: Literal["symptom"] = "symptom"
    severity: int = Field(ge=1, le=5)
    body_area: BodyArea | None = None


class MoodPayload(BaseModel):
    entry_type: Literal["mood"] = "mood"
    score: int = Field(ge=1, le=5)


class MedicationPayload(BaseModel):
    entry_type: Literal["medication"] = "medication"
    drug_name: str = Field(min_length=1, max_length=200)
    dose: str = Field(min_length=1, max_length=200)
    missed_dose: bool = False


class WeightPayload(BaseModel):
    entry_type: Literal["weight"] = "weight"
    weight_grams: int = Field(ge=100, le=120000)
    source: WeightSource


class VetVisitPayload(BaseModel):
    entry_type: Literal["vet_visit"] = "vet_visit"
    reason: str = Field(min_length=1, max_length=500)
    diagnosis: str | None = Field(default=None, max_length=2000)
    follow_up: str | None = Field(default=None, max_length=500)
    vet_name: str | None = Field(default=None, max_length=200)


class FreeNotePayload(BaseModel):
    entry_type: Literal["free_note"] = "free_note"
    text: str = Field(min_length=1, max_length=2000)


JournalEntryPayload = Annotated[
    MealPayload
    | BathroomPayload
    | SymptomPayload
    | MoodPayload
    | MedicationPayload
    | WeightPayload
    | VetVisitPayload
    | FreeNotePayload,
    Field(discriminator="entry_type"),
]

Tags = Annotated[
    list[Annotated[str, Field(min_length=1, max_length=50)]],
    Field(max_length=MAX_TAGS),
]


def validate_symptom_tags(payload: JournalEntryPayload, tags: list[str]) -> None:
    if payload.entry_type == "symptom" and not tags:
        raise ValueError("a symptom entry requires at least one tag")


class JournalEntryCreate(BaseModel):
    payload: JournalEntryPayload
    occurred_at: datetime | None = None
    note: str | None = Field(default=None, max_length=1000)
    tags: Tags = Field(default_factory=list)

    @field_validator("occurred_at")
    @classmethod
    def _occurred_at_must_be_aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("occurred_at must be timezone-aware")
        return value

    @model_validator(mode="after")
    def _symptom_requires_tags(self) -> JournalEntryCreate:
        validate_symptom_tags(self.payload, self.tags)
        return self


class JournalEntryUpdate(BaseModel):
    payload: JournalEntryPayload | None = None
    occurred_at: datetime | None = None
    note: str | None = Field(default=None, max_length=1000)
    tags: Tags | None = None

    @field_validator("payload", "occurred_at", "tags", mode="before")
    @classmethod
    def _reject_explicit_null(cls, value: object) -> object:
        if value is None:
            raise ValueError("cannot be null — omit the field to leave it unchanged")
        return value

    @field_validator("occurred_at")
    @classmethod
    def _occurred_at_must_be_aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("occurred_at must be timezone-aware")
        return value


class JournalEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    pet_id: uuid.UUID
    payload: JournalEntryPayload
    occurred_at: datetime
    note: str | None
    tags: list[str]
    is_concern: bool
    photo_path: str | None
    created_at: datetime
    updated_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def entry_type(self) -> str:
        return self.payload.entry_type

    @computed_field  # type: ignore[prop-decorator]
    @property
    def photo_url(self) -> str | None:
        if self.photo_path is None:
            return None
        base = settings.backend_base_url.rstrip("/")
        version = self.photo_path.rsplit("/", 1)[-1].split(".", 1)[0]
        return f"{base}/pets/{self.pet_id}/journal/{self.id}/photo?v={version}"


class JournalEntryListResponse(BaseModel):
    items: list[JournalEntryRead]
    next_cursor: str | None
    total_matching: int


class InvalidCursorError(ValueError):
    pass


class ListCursor(BaseModel):
    occurred_at: datetime
    entry_id: uuid.UUID

    def encode(self) -> str:
        raw = f"{self.occurred_at.isoformat()}|{self.entry_id}"
        return base64.urlsafe_b64encode(raw.encode()).decode()

    @classmethod
    def decode(cls, token: str) -> ListCursor:
        try:
            raw = base64.urlsafe_b64decode(token.encode()).decode()
            occurred_at_text, _, entry_id_text = raw.partition("|")
            occurred_at = datetime.fromisoformat(occurred_at_text)
            entry_id = uuid.UUID(entry_id_text)
        except (binascii.Error, UnicodeDecodeError, ValueError) as error:
            raise InvalidCursorError("malformed cursor") from error
        if occurred_at.tzinfo is None:
            raise InvalidCursorError("cursor timestamp must be timezone-aware")
        return cls(occurred_at=occurred_at, entry_id=entry_id)

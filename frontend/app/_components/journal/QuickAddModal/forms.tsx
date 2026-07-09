"use client";

import { useId, useState } from "react";
import {
  BATHROOM_COLORS,
  BATHROOM_KINDS,
  BODY_AREAS,
  BRISTOL_SCORES,
  MEAL_CATEGORIES,
  MEAL_CATEGORY_LABELS,
  MOOD_LABELS,
  SEVERITY_LABELS,
  SYMPTOM_TAG_SUGGESTIONS,
  WEIGHT_SOURCES,
  WEIGHT_SOURCE_LABELS,
  type BathroomColor,
  type BathroomKind,
  type BodyArea,
  type MealCategory,
  type WeightSource,
} from "@/lib/journal.constants";
import { kgToGrams } from "@/lib/journal.format";
import { useRadioGroupNav } from "@/lib/useRadioGroupNav";
import type {
  BathroomPayload,
  FreeNotePayload,
  JournalPayload,
  MealPayload,
  MedicationPayload,
  MoodPayload,
  SymptomPayload,
  VetVisitPayload,
  WeightPayload,
} from "@/lib/journal.schemas";
import {
  FieldLabel,
  NotesField,
  PillRow,
  ScoreScale,
  TagPicker,
  TextField,
} from "./primitives";
import styles from "./QuickAddModal.module.css";

export type EntryDraft = {
  payload: JournalPayload;
  tags: string[];
  note: string | null;
};

type CommonFormProps = {
  initialTags?: string[];
  initialNote?: string | null;
  submitting: boolean;
  submitLabel: string;
  onSubmit: (draft: EntryDraft) => void;
};

function normalizeNote(note: string): string | null {
  const trimmed = note.trim();
  return trimmed.length === 0 ? null : trimmed;
}

function SubmitButton({ label, submitting }: { label: string; submitting: boolean }) {
  return (
    <button type="submit" className={styles.submitButton} disabled={submitting}>
      {submitting ? "Saving…" : label}
    </button>
  );
}

function FormError({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <p role="alert" className={styles.formError}>
      {message}
    </p>
  );
}

type MealFormProps = CommonFormProps & {
  initialPayload?: MealPayload;
  recentMeals?: MealPayload[];
};

export function MealForm({
  initialPayload,
  initialTags,
  initialNote,
  recentMeals = [],
  submitting,
  submitLabel,
  onSubmit,
}: MealFormProps) {
  const [foodName, setFoodName] = useState(initialPayload?.food_name ?? "");
  const [brand, setBrand] = useState(initialPayload?.brand ?? "");
  const [amountGrams, setAmountGrams] = useState(
    initialPayload?.amount_grams !== undefined && initialPayload?.amount_grams !== null
      ? String(initialPayload.amount_grams)
      : "",
  );
  const [category, setCategory] = useState<MealCategory>(initialPayload?.category ?? "kibble");
  const [note, setNote] = useState(initialNote ?? "");
  const [error, setError] = useState<string | null>(null);
  const amountId = useId();

  function applyRecent(meal: MealPayload) {
    setFoodName(meal.food_name);
    setBrand(meal.brand ?? "");
    setAmountGrams(meal.amount_grams !== null ? String(meal.amount_grams) : "");
    setCategory(meal.category);
  }

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (foodName.trim().length === 0) {
      setError("Food name is required");
      return;
    }
    const parsedAmount = amountGrams.trim() === "" ? null : Number(amountGrams);
    if (parsedAmount !== null && (!Number.isInteger(parsedAmount) || parsedAmount <= 0)) {
      setError("Amount must be a positive number of grams");
      return;
    }
    onSubmit({
      payload: {
        entry_type: "meal",
        food_name: foodName.trim(),
        brand: normalizeNote(brand),
        amount_grams: parsedAmount,
        category,
      },
      tags: initialTags ?? [],
      note: normalizeNote(note),
    });
  }

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      {recentMeals.length > 0 && (
        <div className={styles.field}>
          <FieldLabel>Repeat from recent</FieldLabel>
          <div className={styles.recentList}>
            {recentMeals.map((meal, index) => (
              <button
                key={`${meal.food_name}-${index}`}
                type="button"
                className={styles.recentItem}
                onClick={() => applyRecent(meal)}
              >
                <span className={styles.recentItemTitle}>{meal.food_name}</span>
                <span className={styles.recentItemMeta}>
                  {MEAL_CATEGORY_LABELS[meal.category]}
                  {meal.amount_grams !== null ? ` · ${meal.amount_grams} g` : ""}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}
      <PillRow
        legend="Category"
        options={MEAL_CATEGORIES.map((value) => ({
          value,
          label: MEAL_CATEGORY_LABELS[value],
        }))}
        value={category}
        onChange={setCategory}
      />
      <TextField label="Food" value={foodName} onChange={setFoodName} placeholder="Food name" maxLength={200} />
      <TextField label="Brand" value={brand} onChange={setBrand} optional maxLength={200} />
      <div className={styles.field}>
        <FieldLabel htmlFor={amountId} optional>
          Amount (g)
        </FieldLabel>
        <input
          id={amountId}
          type="number"
          inputMode="numeric"
          min={1}
          className={styles.textInput}
          value={amountGrams}
          onChange={(event) => setAmountGrams(event.target.value)}
        />
      </div>
      <NotesField value={note} onChange={setNote} placeholder="Appetite, brand swap…" />
      <FormError message={error} />
      <SubmitButton label={submitLabel} submitting={submitting} />
    </form>
  );
}

type BathroomFormProps = CommonFormProps & {
  initialPayload?: BathroomPayload;
};

const BRISTOL_SHAPES: Record<number, string> = {
  1: "M5 11a2 2 0 1 1 4 0 2 2 0 0 1-4 0Zm6-3a2 2 0 1 1 4 0 2 2 0 0 1-4 0Zm6 4a2 2 0 1 1 4 0 2 2 0 0 1-4 0Zm-9 4a2 2 0 1 1 4 0 2 2 0 0 1-4 0Zm6 0a2 2 0 1 1 4 0 2 2 0 0 1-4 0Z",
  2: "M3 11c0-3 4-4 9-4s10 1 10 4-5 5-10 5S3 14 3 11Z",
  3: "M3 11c0-2 4-3 9-3s10 1 10 3-5 4-10 4S3 13 3 11Zm5 0h2m1 0h2m1 0h2m1 0h2",
  4: "M3 11c0-2 4-3 9-3s10 1 10 3-5 4-10 4S3 13 3 11Z",
  5: "M4 12a3 3 0 1 1 6 0 3 3 0 0 1-6 0Zm8-2a3 3 0 1 1 6 0 3 3 0 0 1-6 0Zm-2 5a2.5 2.5 0 1 1 5 0 2.5 2.5 0 0 1-5 0Z",
  6: "M3 12c0-2 3-3 5-2 1-2 4-2 6 0 2-2 5-1 6 1 1 2-1 4-4 4-2 0-3-1-5-1s-3 1-5 1c-2 0-3-1-3-3Z",
  7: "M3 13c2-2 4 0 6 0s4-2 6 0 4-1 6 1",
};

export function BathroomForm({
  initialPayload,
  initialTags,
  initialNote,
  submitting,
  submitLabel,
  onSubmit,
}: BathroomFormProps) {
  const [kind, setKind] = useState<BathroomKind>(initialPayload?.kind ?? "poop");
  const [bristolScore, setBristolScore] = useState<number | null>(
    initialPayload?.bristol_score ?? null,
  );
  const [color, setColor] = useState<BathroomColor | null>(initialPayload?.color ?? null);
  const [note, setNote] = useState(initialNote ?? "");

  function handleKindChange(nextKind: BathroomKind) {
    setKind(nextKind);
    if (nextKind === "pee") {
      setBristolScore(null);
      setColor(null);
    }
  }

  const bristolItemProps = useRadioGroupNav(
    BRISTOL_SCORES.length,
    BRISTOL_SCORES.findIndex((bristol) => bristol.score === bristolScore),
    (index) => setBristolScore(BRISTOL_SCORES[index].score),
  );

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    onSubmit({
      payload: { entry_type: "bathroom", kind, bristol_score: bristolScore, color },
      tags: initialTags ?? [],
      note: normalizeNote(note),
    });
  }

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      <PillRow
        legend="Kind"
        options={BATHROOM_KINDS.map((value) => ({
          value,
          label: value === "poop" ? "Poop" : value === "pee" ? "Pee" : "Both",
        }))}
        value={kind}
        onChange={handleKindChange}
      />
      {kind !== "pee" && (
        <>
          <fieldset className={styles.pillFieldset}>
            <legend className={styles.fieldLabel}>What did it look like?</legend>
            <div className={styles.bristolGrid} role="radiogroup" aria-label="Bristol score">
              {BRISTOL_SCORES.map((bristol, index) => {
                const active = bristol.score === bristolScore;
                return (
                  <button
                    key={bristol.score}
                    type="button"
                    role="radio"
                    aria-checked={active}
                    className={`${styles.bristolButton} ${active ? styles.bristolButtonActive : ""}`}
                    onClick={() => setBristolScore(active ? null : bristol.score)}
                    title={bristol.description}
                    {...bristolItemProps(index)}
                  >
                    {"ideal" in bristol && bristol.ideal && (
                      <span className={styles.idealBadge}>IDEAL</span>
                    )}
                    <svg width="36" height="20" viewBox="0 0 26 22" aria-hidden>
                      <path
                        d={BRISTOL_SHAPES[bristol.score]}
                        fill="currentColor"
                        stroke="currentColor"
                        strokeWidth="0.6"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                    <span className={styles.bristolLabel}>
                      {bristol.score} · {bristol.label}
                    </span>
                  </button>
                );
              })}
            </div>
          </fieldset>
          <PillRow
            legend="Color"
            options={BATHROOM_COLORS.map((value) => ({ value, label: value }))}
            value={color}
            onChange={(value) => setColor(value === color ? null : value)}
          />
        </>
      )}
      <NotesField value={note} onChange={setNote} />
      <SubmitButton label={submitLabel} submitting={submitting} />
    </form>
  );
}

type SymptomFormProps = CommonFormProps & {
  initialPayload?: SymptomPayload;
};

export function SymptomForm({
  initialPayload,
  initialTags,
  initialNote,
  submitting,
  submitLabel,
  onSubmit,
}: SymptomFormProps) {
  const [tags, setTags] = useState<string[]>(initialTags ?? []);
  const [severity, setSeverity] = useState(initialPayload?.severity ?? 3);
  const [bodyArea, setBodyArea] = useState<BodyArea | null>(initialPayload?.body_area ?? null);
  const [note, setNote] = useState(initialNote ?? "");
  const [error, setError] = useState<string | null>(null);

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (tags.length === 0) {
      setError("Pick at least one symptom tag");
      return;
    }
    onSubmit({
      payload: { entry_type: "symptom", severity, body_area: bodyArea },
      tags,
      note: normalizeNote(note),
    });
  }

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      <TagPicker
        legend="What's happening"
        suggestions={SYMPTOM_TAG_SUGGESTIONS}
        value={tags}
        onChange={(next) => {
          setTags(next);
          if (next.length > 0) setError(null);
        }}
      />
      <ScoreScale
        legend="How bad?"
        labels={SEVERITY_LABELS}
        value={severity}
        onChange={setSeverity}
      />
      <fieldset className={styles.pillFieldset}>
        <legend className={styles.fieldLabel}>
          Where on the body<span className={styles.optionalHint}> · optional</span>
        </legend>
        <div className={styles.pillRow}>
          {BODY_AREAS.map((area) => (
            <button
              key={area}
              type="button"
              aria-pressed={area === bodyArea}
              className={`${styles.pill} ${area === bodyArea ? styles.pillActive : ""}`}
              onClick={() => setBodyArea(area === bodyArea ? null : area)}
            >
              {area}
            </button>
          ))}
        </div>
      </fieldset>
      <NotesField value={note} onChange={setNote} placeholder="What you noticed, when it started…" />
      <FormError message={error} />
      <SubmitButton label={submitLabel} submitting={submitting} />
    </form>
  );
}

type MoodFormProps = CommonFormProps & {
  initialPayload?: MoodPayload;
};

export function MoodForm({
  initialPayload,
  initialTags,
  initialNote,
  submitting,
  submitLabel,
  onSubmit,
}: MoodFormProps) {
  const [score, setScore] = useState(initialPayload?.score ?? 3);
  const [note, setNote] = useState(initialNote ?? "");

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    onSubmit({
      payload: { entry_type: "mood", score },
      tags: initialTags ?? [],
      note: normalizeNote(note),
    });
  }

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      <ScoreScale legend="How are they doing?" labels={MOOD_LABELS} value={score} onChange={setScore} />
      <NotesField value={note} onChange={setNote} placeholder="What gave you this read…" />
      <SubmitButton label={submitLabel} submitting={submitting} />
    </form>
  );
}

type MedicationFormProps = CommonFormProps & {
  initialPayload?: MedicationPayload;
  recentMedications?: MedicationPayload[];
};

export function MedicationForm({
  initialPayload,
  initialTags,
  initialNote,
  recentMedications = [],
  submitting,
  submitLabel,
  onSubmit,
}: MedicationFormProps) {
  const [drugName, setDrugName] = useState(initialPayload?.drug_name ?? "");
  const [dose, setDose] = useState(initialPayload?.dose ?? "");
  const [missedDose, setMissedDose] = useState(initialPayload?.missed_dose ?? false);
  const [note, setNote] = useState(initialNote ?? "");
  const [error, setError] = useState<string | null>(null);
  const missedId = useId();

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (drugName.trim().length === 0 || dose.trim().length === 0) {
      setError("Drug name and dose are required");
      return;
    }
    onSubmit({
      payload: {
        entry_type: "medication",
        drug_name: drugName.trim(),
        dose: dose.trim(),
        missed_dose: missedDose,
      },
      tags: initialTags ?? [],
      note: normalizeNote(note),
    });
  }

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      {recentMedications.length > 0 && (
        <div className={styles.field}>
          <FieldLabel>Repeat from recent</FieldLabel>
          <div className={styles.recentList}>
            {recentMedications.map((medication, index) => (
              <button
                key={`${medication.drug_name}-${index}`}
                type="button"
                className={styles.recentItem}
                onClick={() => {
                  setDrugName(medication.drug_name);
                  setDose(medication.dose);
                }}
              >
                <span className={styles.recentItemTitle}>{medication.drug_name}</span>
                <span className={styles.recentItemMeta}>{medication.dose}</span>
              </button>
            ))}
          </div>
        </div>
      )}
      <TextField label="Drug" value={drugName} onChange={setDrugName} maxLength={200} />
      <TextField label="Dose" value={dose} onChange={setDose} placeholder="16 mg" maxLength={200} />
      <div className={styles.checkboxRow}>
        <input
          id={missedId}
          type="checkbox"
          checked={missedDose}
          onChange={(event) => setMissedDose(event.target.checked)}
        />
        <label htmlFor={missedId}>
          <span className={styles.checkboxTitle}>Mark as missed dose</span>
          <span className={styles.checkboxHint}>Forgot, refused, or vomited within an hour</span>
        </label>
      </div>
      <NotesField value={note} onChange={setNote} placeholder="Anything unusual after the dose?" />
      <FormError message={error} />
      <SubmitButton label={submitLabel} submitting={submitting} />
    </form>
  );
}

type WeightFormProps = CommonFormProps & {
  initialPayload?: WeightPayload;
};

export function WeightForm({
  initialPayload,
  initialTags,
  initialNote,
  submitting,
  submitLabel,
  onSubmit,
}: WeightFormProps) {
  const [weightKg, setWeightKg] = useState(
    initialPayload ? String(initialPayload.weight_grams / 1000) : "",
  );
  const [source, setSource] = useState<WeightSource>(initialPayload?.source ?? "home_scale");
  const [note, setNote] = useState(initialNote ?? "");
  const [error, setError] = useState<string | null>(null);
  const weightId = useId();

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const parsed = Number(weightKg);
    if (weightKg.trim() === "" || Number.isNaN(parsed)) {
      setError("Enter a weight in kilograms");
      return;
    }
    const weightGrams = kgToGrams(parsed);
    if (weightGrams < 100 || weightGrams > 120000) {
      setError("Weight must be between 0.1 and 120 kg");
      return;
    }
    onSubmit({
      payload: { entry_type: "weight", weight_grams: weightGrams, source },
      tags: initialTags ?? [],
      note: normalizeNote(note),
    });
  }

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      <div className={styles.field}>
        <FieldLabel htmlFor={weightId}>Weight (kg)</FieldLabel>
        <input
          id={weightId}
          type="number"
          inputMode="decimal"
          step="0.1"
          min={0.1}
          max={120}
          className={`${styles.textInput} ${styles.weightInput}`}
          value={weightKg}
          onChange={(event) => setWeightKg(event.target.value)}
        />
      </div>
      <PillRow
        legend="Where weighed"
        options={WEIGHT_SOURCES.map((value) => ({
          value,
          label: WEIGHT_SOURCE_LABELS[value],
        }))}
        value={source}
        onChange={setSource}
      />
      <NotesField value={note} onChange={setNote} placeholder="Weighed after walk, before breakfast…" />
      <FormError message={error} />
      <SubmitButton label={submitLabel} submitting={submitting} />
    </form>
  );
}

type VetVisitFormProps = CommonFormProps & {
  initialPayload?: VetVisitPayload;
};

const VISIT_REASON_SUGGESTIONS = [
  "Annual exam",
  "Vaccination",
  "Sick visit",
  "Dental",
  "Follow-up",
  "Emergency",
];

export function VetVisitForm({
  initialPayload,
  initialTags,
  initialNote,
  submitting,
  submitLabel,
  onSubmit,
}: VetVisitFormProps) {
  const [reason, setReason] = useState(initialPayload?.reason ?? "");
  const [diagnosis, setDiagnosis] = useState(initialPayload?.diagnosis ?? "");
  const [followUp, setFollowUp] = useState(initialPayload?.follow_up ?? "");
  const [vetName, setVetName] = useState(initialPayload?.vet_name ?? "");
  const [note, setNote] = useState(initialNote ?? "");
  const [error, setError] = useState<string | null>(null);
  const diagnosisId = useId();

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (reason.trim().length === 0) {
      setError("Reason for the visit is required");
      return;
    }
    onSubmit({
      payload: {
        entry_type: "vet_visit",
        reason: reason.trim(),
        diagnosis: normalizeNote(diagnosis),
        follow_up: normalizeNote(followUp),
        vet_name: normalizeNote(vetName),
      },
      tags: initialTags ?? [],
      note: normalizeNote(note),
    });
  }

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      <TextField label="Reason for visit" value={reason} onChange={setReason} maxLength={500} />
      <div className={styles.pillRow}>
        {VISIT_REASON_SUGGESTIONS.map((suggestion) => (
          <button
            key={suggestion}
            type="button"
            className={`${styles.pill} ${reason === suggestion ? styles.pillActive : ""}`}
            onClick={() => setReason(suggestion)}
          >
            {suggestion}
          </button>
        ))}
      </div>
      <div className={styles.field}>
        <FieldLabel htmlFor={diagnosisId} optional>
          Diagnosis & notes
        </FieldLabel>
        <textarea
          id={diagnosisId}
          className={styles.textArea}
          rows={4}
          maxLength={2000}
          value={diagnosis}
          onChange={(event) => setDiagnosis(event.target.value)}
        />
      </div>
      <TextField label="Follow-up" value={followUp} onChange={setFollowUp} optional placeholder="In 2 weeks · May 29" maxLength={500} />
      <TextField label="Vet" value={vetName} onChange={setVetName} optional placeholder="Dr. Patel" maxLength={200} />
      <NotesField value={note} onChange={setNote} />
      <FormError message={error} />
      <SubmitButton label={submitLabel} submitting={submitting} />
    </form>
  );
}

type FreeNoteFormProps = CommonFormProps & {
  initialPayload?: FreeNotePayload;
};

export function FreeNoteForm({
  initialPayload,
  initialTags,
  submitting,
  submitLabel,
  onSubmit,
}: FreeNoteFormProps) {
  const [text, setText] = useState(initialPayload?.text ?? "");
  const [tags, setTags] = useState<string[]>(initialTags ?? []);
  const [error, setError] = useState<string | null>(null);
  const textId = useId();

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (text.trim().length === 0) {
      setError("Write something first");
      return;
    }
    onSubmit({
      payload: { entry_type: "free_note", text: text.trim() },
      tags,
      note: null,
    });
  }

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      <div className={styles.field}>
        <FieldLabel htmlFor={textId}>Anything you want to remember</FieldLabel>
        <textarea
          id={textId}
          className={styles.textArea}
          rows={6}
          maxLength={2000}
          autoFocus
          value={text}
          onChange={(event) => setText(event.target.value)}
        />
      </div>
      <button type="button" className={styles.secondaryButton} disabled>
        Dictate <span className={styles.soonBadge}>SOON</span>
      </button>
      <TagPicker legend="Tags" suggestions={[]} value={tags} onChange={setTags} />
      <FormError message={error} />
      <SubmitButton label={submitLabel} submitting={submitting} />
    </form>
  );
}

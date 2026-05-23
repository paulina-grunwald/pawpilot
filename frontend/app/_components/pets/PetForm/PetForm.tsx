"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useId, useState, type ReactNode } from "react";
import { Controller, useForm, type Control, type FieldError } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  PetsError,
  createPet,
  deletePetPhoto,
  updatePet,
  uploadPetPhoto,
  type PetSex,
} from "@/lib/pets";
import {
  petFormSchema,
  toCreateInput,
  toUpdateInput,
  type PetFormInput,
} from "@/lib/pets.schemas";
import { PhotoUploader } from "../../media/PhotoUploader";
import { BirthdayField } from "../BirthdayField";
import { BreedTypeahead } from "../BreedTypeahead";
import styles from "./PetForm.module.css";

type PetFormProps =
  | { mode: "create" }
  | {
      mode: "edit";
      petId: string;
      initialValues: PetFormInput;
      existingPhotoUrl?: string | null;
    };

function buildDefaultValues(props: PetFormProps): PetFormInput {
  if (props.mode === "edit") return props.initialValues;
  return {
    name: "",
    breedOther: "",
    birthday: "",
    sex: "female",
    spayedNeutered: true,
    weightKg: 10,
    notes: "",
  };
}

type FieldProps = {
  label: string;
  help?: string;
  error?: FieldError | undefined;
  children: (controlIds: { inputId: string; describedBy: string | undefined }) => ReactNode;
};

function Field({ label, help, error, children }: FieldProps) {
  const generated = useId();
  const inputId = `pet-field-${generated}`;
  const errorId = `${inputId}-error`;
  const helpId = `${inputId}-help`;
  const describedBy =
    [error ? errorId : null, help && !error ? helpId : null].filter(Boolean).join(" ") || undefined;
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={inputId} className={styles.fieldLabel}>
        {label}
      </label>
      {children({ inputId, describedBy })}
      {help && !error && (
        <p id={helpId} className={styles.fieldHelp}>
          {help}
        </p>
      )}
      {error && (
        <p id={errorId} role="alert" className={styles.fieldError}>
          {error.message}
        </p>
      )}
    </div>
  );
}

type SegmentedGroupProps<T extends string | boolean> = {
  label: string;
  control: Control<PetFormInput>;
  name: "sex" | "spayedNeutered";
  options: Array<{ value: T; label: string }>;
};

function SegmentedGroup<T extends string | boolean>({
  label,
  control,
  name,
  options,
}: SegmentedGroupProps<T>) {
  const labelId = useId();
  return (
    <div className="flex flex-col gap-1.5">
      <span id={labelId} className={styles.fieldLabel}>
        {label}
      </span>
      <Controller
        control={control}
        name={name}
        render={({ field }) => (
          <div role="group" aria-labelledby={labelId} className="flex gap-2">
            {options.map((option) => {
              const isPressed = field.value === option.value;
              return (
                <button
                  key={String(option.value)}
                  type="button"
                  className={styles.segButton}
                  aria-pressed={isPressed}
                  onClick={() => field.onChange(option.value)}
                >
                  {option.label}
                </button>
              );
            })}
          </div>
        )}
      />
    </div>
  );
}

export function PetForm(props: PetFormProps) {
  const router = useRouter();
  const [formError, setFormError] = useState<string | null>(null);
  const [photoFile, setPhotoFile] = useState<File | null>(null);
  const [removeExistingPhoto, setRemoveExistingPhoto] = useState(false);
  const [createdPetId, setCreatedPetId] = useState<string | null>(null);
  const existingPhotoUrl = props.mode === "edit" ? props.existingPhotoUrl ?? null : null;

  const {
    register,
    handleSubmit,
    control,
    formState: { errors, isSubmitting },
  } = useForm<PetFormInput>({
    resolver: zodResolver(petFormSchema),
    mode: "onSubmit",
    defaultValues: buildDefaultValues(props),
  });

  function describePhotoError(error: PetsError): string {
    if (error.code === "PET_PHOTO_UNSUPPORTED_MEDIA_TYPE") {
      return "We can only accept PNG, JPG, or WEBP images.";
    }
    if (error.code === "PET_PHOTO_TOO_LARGE") {
      return "That photo is too large — keep it under 5 MB.";
    }
    return "We saved the pet but couldn't upload the photo. Try again from the edit page.";
  }

  async function onSubmit(values: PetFormInput) {
    setFormError(null);
    const existingPetId = props.mode === "edit" ? props.petId : createdPetId;
    try {
      const savedPet = existingPetId
        ? await updatePet(existingPetId, toUpdateInput(values))
        : await createPet(toCreateInput(values));

      if (props.mode === "create" && !createdPetId) {
        setCreatedPetId(savedPet.id);
      }

      try {
        if (photoFile) {
          await uploadPetPhoto(savedPet.id, photoFile);
        } else if (existingPetId && removeExistingPhoto) {
          await deletePetPhoto(existingPetId);
        }
      } catch (photoError) {
        const message =
          photoError instanceof PetsError
            ? describePhotoError(photoError)
            : "We saved the pet but couldn't upload the photo. Try again from the edit page.";
        setFormError(message);
        setPhotoFile(null);
        router.refresh();
        return;
      }

      router.replace(`/pets/${savedPet.id}`);
      router.refresh();
    } catch (caught) {
      if (caught instanceof PetsError) {
        setFormError(
          caught.code === "PET_VALIDATION_ERROR"
            ? "Something didn't validate. Double-check the fields above."
            : "We couldn't save this pet. Try again in a moment.",
        );
        return;
      }
      setFormError("We couldn't save this pet. Try again in a moment.");
    }
  }

  const isCreate = props.mode === "create";
  const backHref = isCreate ? "/dashboard" : `/pets/${props.petId}`;
  const backLabel = isCreate ? "← Back to dashboard" : "← Back to pet";
  const title = isCreate ? "Add a pet" : "Edit pet";
  const submitLabel = isCreate ? "Save pet" : "Save changes";
  const submittingLabel = isCreate ? "Saving…" : "Saving changes…";

  return (
    <main className={`container-x ${styles.page}`}>
      <p className={styles.backLink}>
        <Link href={backHref}>{backLabel}</Link>
      </p>
      <h1 className={`${styles.title} display`}>{title}</h1>
      {isCreate && (
        <p className={styles.subtitle}>Just the basics for now — you can edit anytime.</p>
      )}

      <form noValidate onSubmit={handleSubmit(onSubmit)} className="mt-2">
        <div className="flex flex-col gap-[18px]">
          <div className="flex flex-col gap-1.5">
            <span className={styles.fieldLabel}>Photo</span>
            <PhotoUploader
              existingPhotoUrl={existingPhotoUrl}
              file={photoFile}
              removeRequested={removeExistingPhoto}
              onFileChange={(next) => {
                setPhotoFile(next);
                if (next) setRemoveExistingPhoto(false);
              }}
              onRemoveExisting={
                props.mode === "edit" ? () => setRemoveExistingPhoto(true) : undefined
              }
              altText={`${props.mode === "edit" ? props.initialValues.name : "Pet"} photo preview`}
            />
          </div>

          <Field label="Name" error={errors.name}>
            {({ inputId, describedBy }) => (
              <input
                id={inputId}
                type="text"
                className={styles.input}
                aria-invalid={errors.name ? "true" : undefined}
                aria-describedby={describedBy}
                {...register("name")}
              />
            )}
          </Field>

          <Field
            label="Breed"
            help="Pick from the list or type your own — pop in “Mixed / unknown” if you're not sure."
            error={errors.breedOther}
          >
            {({ inputId, describedBy }) => (
              <Controller
                control={control}
                name="breedOther"
                render={({ field }) => (
                  <BreedTypeahead
                    inputId={inputId}
                    value={field.value ?? ""}
                    onChange={field.onChange}
                    onBlur={field.onBlur}
                    invalid={!!errors.breedOther}
                    describedBy={describedBy}
                  />
                )}
              />
            )}
          </Field>

          <Field
            label="Birthday"
            help="We use this to figure out life stage."
            error={errors.birthday}
          >
            {({ inputId, describedBy }) => (
              <Controller
                control={control}
                name="birthday"
                render={({ field }) => (
                  <BirthdayField
                    inputId={inputId}
                    value={field.value ?? ""}
                    onChange={field.onChange}
                    onBlur={field.onBlur}
                    invalid={!!errors.birthday}
                    describedBy={describedBy}
                  />
                )}
              />
            )}
          </Field>

          <div className="grid grid-cols-2 gap-4">
            <SegmentedGroup<PetSex>
              label="Sex"
              control={control}
              name="sex"
              options={[
                { value: "female", label: "Female" },
                { value: "male", label: "Male" },
              ]}
            />
            <SegmentedGroup<boolean>
              label="Spayed / neutered"
              control={control}
              name="spayedNeutered"
              options={[
                { value: true, label: "Yes" },
                { value: false, label: "No" },
              ]}
            />
          </div>

          <Field
            label="Weight"
            help="In kilograms. Don't sweat it — you can update this later."
            error={errors.weightKg}
          >
            {({ inputId, describedBy }) => (
              <div className="flex items-center gap-3">
                <input
                  id={inputId}
                  type="number"
                  step="0.1"
                  min="0.1"
                  max="120"
                  className={styles.input}
                  style={{ maxWidth: 140 }}
                  aria-invalid={errors.weightKg ? "true" : undefined}
                  aria-describedby={describedBy}
                  {...register("weightKg", { valueAsNumber: true })}
                />
                <span className={styles.unit}>kg</span>
              </div>
            )}
          </Field>

          <Field
            label="Notes"
            help="Allergies, quirks, vet name — anything you want PawPilot to remember. Optional."
            error={errors.notes}
          >
            {({ inputId, describedBy }) => (
              <textarea
                id={inputId}
                className={styles.textarea}
                aria-invalid={errors.notes ? "true" : undefined}
                aria-describedby={describedBy}
                {...register("notes")}
              />
            )}
          </Field>
        </div>

        {formError && (
          <p role="alert" className={styles.formError}>
            {formError}
          </p>
        )}

        <div className={styles.actions}>
          <button type="submit" className={styles.submit} disabled={isSubmitting}>
            {isSubmitting ? submittingLabel : submitLabel}
          </button>
          <Link href={backHref} className={styles.cancel}>
            Cancel
          </Link>
        </div>
      </form>
    </main>
  );
}

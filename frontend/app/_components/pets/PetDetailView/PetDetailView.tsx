import Link from "next/link";
import type { ReactNode } from "react";
import type { PetDetailView as PetDetailData } from "@/lib/pets.format";
import { Chip } from "../Chip";
import { PetActions } from "../PetActions";
import { PhotoPlaceholder } from "../PhotoPlaceholder";
import { TractiveUpload } from "../TractiveUpload";
import styles from "./PetDetailView.module.css";

export type { PetDetailData };

type FactStatProps = {
  label: string;
  value: string;
  mono?: boolean;
};

function FactStat({ label, value, mono }: FactStatProps) {
  return (
    <div>
      <p className={styles.statLabel}>{label}</p>
      <p className={`${styles.statValue} ${mono ? "mono" : ""}`}>{value}</p>
    </div>
  );
}

type PetDetailViewProps = {
  pet: PetDetailData;
  journalCard?: ReactNode;
};

export function PetDetailView({ pet, journalCard }: PetDetailViewProps) {
  return (
    <main className={`container-x ${styles.page}`}>
      <p className="m-0 mb-2 text-[13px] text-muted">
        <Link href="/dashboard" className="text-muted no-underline">
          ← Dashboard
        </Link>
      </p>

      <section aria-label="Pet overview" className={styles.hero}>
        <div className={styles.heroPhoto}>
          {pet.photoUrl ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img className={styles.heroPhotoImage} src={pet.photoUrl} alt={`${pet.name}'s photo`} />
          ) : (
            <PhotoPlaceholder label={pet.name} radius={16} />
          )}
        </div>
        <div>
          <div className="flex flex-wrap items-baseline gap-3.5">
            <h1 className={`${styles.heroName} display`}>{pet.name}</h1>
            <Chip variant="forest">{pet.lifeStage}</Chip>
          </div>
          <p className={styles.heroSubtitle}>{pet.breed}</p>

          <div className={styles.statsRow}>
            <FactStat label="Age" value={pet.ageDisplay} />
            <FactStat label="Birthday" value={pet.birthdayDisplay} mono />
            <FactStat label="Weight" value={pet.weightDisplay} />
            <FactStat label="Sex" value={`${pet.sexDisplay} · ${pet.spayedNeuteredDisplay}`} />
          </div>

          <div className={styles.actions}>
            <PetActions petId={pet.id} petName={pet.name} />
          </div>
        </div>
      </section>

      <section aria-label="Notes and wearable" className={styles.body}>
        <article className={styles.card}>
          <h2 className={`${styles.cardHeading} display`}>Notes</h2>
          <p className={styles.notesText}>{pet.notes || "No notes yet."}</p>
          <Link href={`/pets/${pet.id}/edit`} className={styles.editLink}>
            Edit notes
          </Link>
        </article>

        <article className={styles.card}>
          <h2 className={`${styles.cardHeading} display`}>Wearable</h2>
          <TractiveUpload petId={pet.id} />
        </article>

        {journalCard}
      </section>

      <p className={styles.footnote}>
        Vaccinations and interaction history land in a later release.
      </p>
    </main>
  );
}

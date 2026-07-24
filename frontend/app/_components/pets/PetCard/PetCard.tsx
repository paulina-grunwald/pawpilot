import Link from "next/link";
import { Chip } from "../Chip";
import styles from "./PetCard.module.css";

export type PetCardData = {
  id: string;
  name: string;
  breed: string;
  ageDisplay: string;
  weightDisplay: string;
  sexDisplay: string;
  lifeStage: string;
  photoUrl?: string | null;
};

type PetCardProps = {
  pet: PetCardData;
  href?: string;
};

function initialsFor(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
}

export function PetCard({ pet, href }: PetCardProps) {
  const photoSlot = pet.photoUrl ? (
    // eslint-disable-next-line @next/next/no-img-element
    <img className={styles.photoImage} src={pet.photoUrl} alt={`${pet.name}'s photo`} />
  ) : (
    <span aria-hidden className={styles.initials}>
      {initialsFor(pet.name)}
    </span>
  );

  const body = (
    <>
      <div className={styles.photo}>{photoSlot}</div>
      <div>
        <div className={styles.titleRow}>
          <h2 className={`${styles.name} display`}>{pet.name}</h2>
          <Chip variant="default">
            <span aria-hidden className={styles.chipDot} style={{ background: "var(--forest)" }} />
            {pet.lifeStage}
          </Chip>
        </div>
        <p className={styles.meta}>
          {pet.breed} · {pet.ageDisplay} · {pet.weightDisplay} · {pet.sexDisplay}
        </p>
      </div>
    </>
  );

  const linkHref = href ?? `/pets/${pet.id}`;
  return (
    <Link href={linkHref} className={styles.card} aria-label={`Open ${pet.name}'s profile`}>
      {body}
    </Link>
  );
}

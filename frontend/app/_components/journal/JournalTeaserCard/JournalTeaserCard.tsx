import Link from "next/link";
import type { JournalEntryRead } from "@/lib/journal.schemas";
import { EntryCard } from "../EntryCard";
import styles from "./JournalTeaserCard.module.css";

type JournalTeaserCardProps = {
  petId: string;
  petName: string;
  entries: JournalEntryRead[];
};

export function JournalTeaserCard({ petId, petName, entries }: JournalTeaserCardProps) {
  return (
    <article className={styles.card}>
      <h2 className={`${styles.heading} display`}>Journal</h2>
      {entries.length === 0 ? (
        <p className={styles.empty}>
          No entries yet — logging meals, mood, and symptoms helps PawPilot spot when
          something&rsquo;s off.
        </p>
      ) : (
        <div className={styles.entries}>
          {entries.slice(0, 3).map((entry) => (
            <EntryCard key={entry.id} entry={entry} />
          ))}
        </div>
      )}
      <Link href={`/pets/${petId}/journal`} className={styles.openLink}>
        Open {petName}&rsquo;s journal →
      </Link>
    </article>
  );
}

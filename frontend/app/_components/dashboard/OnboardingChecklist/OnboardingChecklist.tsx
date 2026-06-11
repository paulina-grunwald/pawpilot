import Link from "next/link";
import styles from "./OnboardingChecklist.module.css";

type ChecklistStep = {
  number: number;
  title: string;
  description: string;
  done: boolean;
  active?: boolean;
  disabled?: boolean;
};

type OnboardingChecklistProps = {
  userEmail: string;
};

function buildSteps(userEmail: string): ChecklistStep[] {
  return [
    {
      number: 1,
      title: "Create your account",
      description: `You're signed in as ${userEmail}`,
      done: true,
    },
    {
      number: 2,
      title: "Add your first dog",
      description: "Tell us about your pup — breed, age, weight. Takes about a minute.",
      done: false,
      active: true,
    },
    {
      number: 3,
      title: "Connect your Tractive collar",
      description: "See activity, sleep, and vitals on your dashboard.",
      done: false,
      disabled: true,
    },
    {
      number: 4,
      title: "Ask your first question",
      description: "Symptoms, food safety, behavior — anything.",
      done: false,
      disabled: true,
    },
  ];
}

export function OnboardingChecklist({ userEmail }: OnboardingChecklistProps) {
  const steps = buildSteps(userEmail);

  return (
    <main className={styles.page} aria-label="Onboarding">
      <div className="mb-10">
        <p className={styles.eyebrow}>Welcome to PawPilot</p>
        <h1 className={`${styles.headline} display`}>Let&rsquo;s get your dog set up.</h1>
        <p className={styles.lede}>
          Three quick steps and PawPilot will know your pup well enough to answer questions the
          way a vet who&rsquo;s seen them would.
        </p>
      </div>

      <ol className={styles.list}>
        {steps.map((step) => {
          const stepClasses = [
            styles.step,
            step.active ? styles.stepActive : "",
            step.disabled ? styles.stepDisabled : "",
          ]
            .filter(Boolean)
            .join(" ");
          const badgeClasses = [
            styles.badge,
            step.done ? styles.badgeDone : "",
            step.active ? styles.badgeActive : "",
          ]
            .filter(Boolean)
            .join(" ");
          const titleClasses = [styles.stepTitle, step.done ? styles.stepTitleDone : ""]
            .filter(Boolean)
            .join(" ");
          const statusLabel = step.done
            ? `Step ${step.number}: complete`
            : `Step ${step.number}`;
          return (
            <li key={step.number} className={stepClasses}>
              <div className={badgeClasses} role="img" aria-label={statusLabel}>
                <span aria-hidden>{step.done ? "✓" : step.number}</span>
              </div>
              <div className={styles.stepBody}>
                <div className={titleClasses}>{step.title}</div>
                <div className={styles.stepDescription}>{step.description}</div>
                {step.active && (
                  <Link href="/pets/new" className={styles.cta}>
                    Add pet
                    <span aria-hidden>→</span>
                  </Link>
                )}
              </div>
            </li>
          );
        })}
      </ol>

      <p className={styles.footnote}>
        You can skip Tractive and questions for now — we&rsquo;ll show them here when you&rsquo;re
        ready.
      </p>
    </main>
  );
}

import Link from "next/link";
import { ChatView } from "@/app/_components/chat/ChatView";
import { toPetPickerOption } from "@/lib/pets";
import { requireCurrentUser } from "@/lib/auth.server";
import { fetchPetsForCurrentUser } from "@/lib/pets.server";

export default async function ChatPage() {
  await requireCurrentUser();
  const pets = await fetchPetsForCurrentUser();

  if (pets.length === 0) {
    return (
      <main className="container-x" style={{ paddingTop: 64, paddingBottom: 64 }}>
        <h1 className="display text-ink" style={{ fontSize: 28, margin: 0 }}>
          Ask PawPilot
        </h1>
        <p className="text-muted" style={{ marginTop: 8, marginBottom: 20 }}>
          Add a dog first so PawPilot can give personalized, remembered answers.
        </p>
        <Link href="/pets/new" className="text-blue" style={{ fontWeight: 600 }}>
          + Add a dog
        </Link>
      </main>
    );
  }

  return <ChatView pets={pets.map(toPetPickerOption)} />;
}

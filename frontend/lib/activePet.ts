/**
 * localStorage key holding the id of the pet the user last focused. Shared by
 * the dashboard, the journal FAB, and the navbar journal link so they all point
 * at the same dog.
 */
export function activePetStorageKey(userId: string): string {
  return `pawpilot:active-pet:${userId}`;
}

const PET_SCOPED_ROUTE = /^\/(?:dashboard|pets)\/([^/]+)/;

/**
 * Pull the focused pet id out of a `/dashboard/[petId]` or `/pets/[petId]` path.
 * Returns null on routes that don't name a pet (`/chat`, `/pets/new`, `/dashboard`).
 */
export function petIdFromPathname(pathname: string): string | null {
  const candidate = PET_SCOPED_ROUTE.exec(pathname)?.[1];
  if (!candidate || candidate === "new") return null;
  return candidate;
}

export const ENTRY_TYPES = [
  "meal",
  "bathroom",
  "symptom",
  "mood",
  "medication",
  "weight",
  "vet_visit",
  "free_note",
] as const;

export type EntryType = (typeof ENTRY_TYPES)[number];

export type EntryTypeMeta = {
  label: string;
  subtitle: string;
  accentVar: string;
};

export const ENTRY_TYPE_META: Record<EntryType, EntryTypeMeta> = {
  meal: { label: "Meal", subtitle: "kibble · wet · treat", accentVar: "--warm" },
  bathroom: { label: "Bathroom", subtitle: "pee · poop · both", accentVar: "--ochre" },
  symptom: { label: "Symptom", subtitle: "limp · scratch · vomit", accentVar: "--terracotta" },
  mood: { label: "Mood", subtitle: "how they seem", accentVar: "--forest-light" },
  medication: { label: "Medication", subtitle: "doses & misses", accentVar: "--blue-deep" },
  weight: { label: "Weight", subtitle: "home scale or vet", accentVar: "--forest" },
  vet_visit: { label: "Vet visit", subtitle: "reason · diagnosis", accentVar: "--blue" },
  free_note: { label: "Free note", subtitle: "anything else", accentVar: "--muted" },
};

export const SYMPTOM_TAG_SUGGESTIONS = [
  "scratch",
  "head-shake",
  "limp",
  "vomit",
  "lethargy",
  "coughing",
  "sneezing",
  "discharge",
  "swelling",
  "hot-spot",
] as const;

export const BODY_AREAS = [
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
] as const;

export type BodyArea = (typeof BODY_AREAS)[number];

export const MEAL_CATEGORIES = ["kibble", "wet", "home_cooked", "treat"] as const;
export type MealCategory = (typeof MEAL_CATEGORIES)[number];

export const MEAL_CATEGORY_LABELS: Record<MealCategory, string> = {
  kibble: "Kibble",
  wet: "Wet",
  home_cooked: "Home",
  treat: "Treat",
};

export const BATHROOM_KINDS = ["poop", "pee", "both"] as const;
export type BathroomKind = (typeof BATHROOM_KINDS)[number];

export const BATHROOM_COLORS = ["brown", "dark", "mustard", "orange", "black", "red"] as const;
export type BathroomColor = (typeof BATHROOM_COLORS)[number];

export const BRISTOL_SCORES = [
  { score: 1, label: "pebbles", description: "hard, separate lumps" },
  { score: 2, label: "lumpy", description: "sausage but lumpy" },
  { score: 3, label: "cracked", description: "sausage with cracks" },
  { score: 4, label: "smooth", description: "smooth, soft sausage", ideal: true },
  { score: 5, label: "soft", description: "soft blobs" },
  { score: 6, label: "mushy", description: "fluffy, ragged edges" },
  { score: 7, label: "liquid", description: "watery, no solids" },
] as const;

export const SEVERITY_LABELS: Record<number, string> = {
  1: "barely",
  2: "mild",
  3: "moderate",
  4: "strong",
  5: "severe",
};

export const MOOD_LABELS: Record<number, string> = {
  1: "withdrawn",
  2: "subdued",
  3: "normal",
  4: "clingy",
  5: "playful",
};

export const WEIGHT_SOURCES = ["home_scale", "vet"] as const;
export type WeightSource = (typeof WEIGHT_SOURCES)[number];

export const WEIGHT_SOURCE_LABELS: Record<WeightSource, string> = {
  home_scale: "Home scale",
  vet: "At the vet",
};

export const MAX_TAGS = 20;
export const MAX_TAG_LENGTH = 50;
export const MAX_NOTE_LENGTH = 1000;

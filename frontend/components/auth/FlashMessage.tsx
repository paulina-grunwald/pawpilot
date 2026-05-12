import { flashCopy } from "./errorCopy";

type FlashTone = "success" | "info";

type FlashMessageProps = {
  flashKey: string | null | undefined;
  tone?: FlashTone;
};

export function FlashMessage({ flashKey, tone = "success" }: FlashMessageProps) {
  if (!flashKey) return null;
  const message = flashCopy[flashKey];
  if (!message) return null;
  const isSuccess = tone === "success";
  return (
    <div
      role="status"
      className="rounded-lg border px-3 py-2 text-[13px]"
      style={{
        background: isSuccess
          ? "color-mix(in srgb, var(--forest) 8%, transparent)"
          : "color-mix(in srgb, var(--blue) 8%, transparent)",
        borderColor: isSuccess ? "var(--forest)" : "var(--blue)",
        color: isSuccess ? "var(--forest-deep)" : "var(--blue-deep)",
      }}
    >
      {message}
    </div>
  );
}

export function inputClass(hasError: boolean): string {
  return [
    "block w-full rounded-xl border bg-base-200 px-3 py-2.5 text-base-content transition-colors placeholder:text-base-content/45 focus:outline-none focus:ring-2",
    hasError
      ? "border-error focus:ring-error/35"
      : "border-base-300 focus:border-primary focus:ring-primary/25",
  ].join(" ");
}

export function textareaClass(hasError: boolean): string {
  return [
    "min-h-28 w-full resize-y rounded-xl border bg-base-200 px-3 py-2.5 text-base-content transition-colors placeholder:text-base-content/45 focus:outline-none focus:ring-2",
    hasError
      ? "border-error focus:ring-error/35"
      : "border-base-300 focus:border-primary focus:ring-primary/25",
  ].join(" ");
}

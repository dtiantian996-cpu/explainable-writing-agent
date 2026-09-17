export function roundIeltsBand(value: number): number {
  return Math.round((value + Number.EPSILON) * 2) / 2;
}

export function formatIeltsBand(value?: number | null): string {
  if (value == null || Number.isNaN(value)) return "--";
  return roundIeltsBand(value).toFixed(1);
}

export function formatIeltsBandWithScale(value?: number | null): string {
  const formatted = formatIeltsBand(value);
  return formatted === "--" ? "--" : `${formatted} / 9`;
}

export function calculateIeltsBandGap(target: number, current: number): number {
  return Math.max(0, roundIeltsBand(target) - roundIeltsBand(current));
}

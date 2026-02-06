import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatMoney(value: number): string {
  if (value >= 100000000) {
    return `${(value / 100000000).toFixed(1)}억원`;
  }
  if (value >= 10000) {
    return `${Math.round(value / 10000).toLocaleString()}만원`;
  }
  return `${value.toLocaleString()}원`;
}

export function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

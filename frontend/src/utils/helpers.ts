import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDelay(min: number): string {
  if (min < 1) return '< 1m'
  if (min < 60) return `${min.toFixed(1)}m`
  return `${(min / 60).toFixed(1)}h`
}

export function delayColor(min: number): string {
  if (min > 30) return 'text-rail-red'
  if (min > 10) return 'text-rail-amber'
  return 'text-rail-green'
}

export function delayBarColor(min: number): string {
  if (min > 30) return 'bg-rail-red'
  if (min > 10) return 'bg-rail-amber'
  return 'bg-rail-green'
}

export function congestionColor(score: number): string {
  if (score > 0.85) return 'text-rail-red'
  if (score > 0.65) return 'text-rail-amber'
  if (score > 0.4)  return 'text-rail-cyan'
  return 'text-rail-green'
}

export function congestionBarColor(score: number): string {
  if (score > 0.85) return 'bg-rail-red'
  if (score > 0.65) return 'bg-rail-amber'
  if (score > 0.4)  return 'bg-rail-cyan'
  return 'bg-rail-green'
}

export function congestionLabel(score: number): string {
  if (score > 0.85) return 'CRITICAL'
  if (score > 0.65) return 'HIGH'
  if (score > 0.40) return 'MEDIUM'
  return 'LOW'
}

export function riskPill(risk: string): string {
  if (risk === 'HIGH' || risk === 'CRITICAL') return 'pill-red'
  if (risk === 'MEDIUM' || risk === 'MODERATE') return 'pill-amber'
  return 'pill-green'
}

export function statusColor(status: string): string {
  if (status === 'ON_TIME') return 'text-rail-green'
  if (status === 'SLIGHTLY_LATE') return 'text-rail-amber'
  if (status === 'LATE') return 'text-rail-red'
  return 'text-rail-red'
}

export function formatIST(): string {
  return new Date().toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata', hour12: false })
}

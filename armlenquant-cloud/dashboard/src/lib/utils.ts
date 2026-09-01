import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// Format date in Tbilisi timezone
export function formatDateInTbilisi(date: string | Date): string {
  const d = new Date(date)
  return d.toLocaleString('en-US', {
    timeZone: 'Asia/Tbilisi',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

// Format relative time in Tbilisi context
export function formatDistanceToNowInTbilisi(date: string | Date): string {
  const d = new Date(date)
  const now = new Date()
  const diffMs = now.getTime() - d.getTime()
  const diffHours = diffMs / (1000 * 60 * 60)

  if (diffHours < 1) {
    const diffMinutes = Math.floor(diffMs / (1000 * 60))
    return `${diffMinutes} minutes ago`
  } else if (diffHours < 24) {
    const diffHoursRounded = Math.floor(diffHours)
    return `${diffHoursRounded} hours ago`
  } else {
    const diffDays = Math.floor(diffHours / 24)
    return `${diffDays} days ago`
  }
}

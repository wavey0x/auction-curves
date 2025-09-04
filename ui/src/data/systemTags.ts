/**
 * System-defined address tags for common protocol addresses
 * These are read-only tags that cannot be modified by users
 */

export const SYSTEM_TAGS: Record<string, string> = {
  // CoW Protocol
  '0x9008d19f58aabd9ed0d60971565aa8510560ab41': '🐮 Cowswap Settlement',
}

/**
 * Get all system tags (used for display purposes)
 */
export function getSystemTags(): Record<string, string> {
  return SYSTEM_TAGS
}

/**
 * Check if an address has a system tag
 */
export function hasSystemTag(address: string): boolean {
  return address.toLowerCase() in SYSTEM_TAGS
}

/**
 * Get system tag for an address (case-insensitive)
 */
export function getSystemTag(address: string): string | null {
  return SYSTEM_TAGS[address.toLowerCase()] || null
}
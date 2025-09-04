import { useAddressTags } from '../context/AddressTagsContext';
import { formatAddress } from '../lib/utils';

/**
 * Custom hook for getting display names and formatting for addresses
 * Handles tag lookup, formatting, and truncation according to the specification
 */
export function useAddressTag() {
  const { getTag, hasUserTag, hasSystemTag } = useAddressTags();

  /**
   * Get the best display name for an address
   * Priority: User tag > System tag > Formatted address
   */
  const getDisplayName = (address: string, options: {
    showFullAddress?: boolean;
    addressLength?: number;
    maxTagLength?: number;
  } = {}) => {
    const {
      showFullAddress = false,
      addressLength = 5,
      maxTagLength = 9
    } = options;

    const tag = getTag(address);
    
    if (tag) {
      // Format tag according to spec: truncate from end with ".."
      return formatTag(tag, maxTagLength);
    }
    
    // No tag found, use formatted address
    return showFullAddress ? address : formatAddress(address, addressLength);
  };

  /**
   * Get metadata about an address's tag status
   */
  const getTagInfo = (address: string) => {
    const tag = getTag(address);
    const isUserTag = hasUserTag(address);
    const isSystemTag = hasSystemTag(address);
    
    return {
      tag,
      hasTag: !!tag,
      isUserTag,
      isSystemTag,
      tagType: isUserTag ? 'user' as const : isSystemTag ? 'system' as const : null
    };
  };

  /**
   * Check if an address should show a tag badge/indicator
   */
  const shouldShowTagIndicator = (address: string): boolean => {
    return !!getTag(address);
  };

  return {
    getDisplayName,
    getTagInfo,
    shouldShowTagIndicator,
    getTag,
    hasUserTag,
    hasSystemTag
  };
}

/**
 * Format a tag according to the specification:
 * - Allow up to maxLength content characters (treating emojis as 1 character)
 * - If longer, truncate from end and append ".." (total display = maxLength + 2)
 * - Examples: "HELLO_WORLD" -> "HELLO_WOR.." (9 content + 2 = 11 total)
 *            "🐮 Cowswap Settlement" -> "🐮 Cowswap.." (9 content + 2 = 11 total)
 */
export function formatTag(tag: string, maxLength: number = 9): string {
  // Count visual characters (treating emojis as 1 character)
  const visualLength = getVisualLength(tag);
  
  if (visualLength <= maxLength) {
    return tag;
  }
  
  // Truncate to exactly maxLength content characters, then append ".."
  return truncateToVisualLength(tag, maxLength) + '..';
}

/**
 * Get the visual length of a string, treating emojis as 1 character each
 */
function getVisualLength(str: string): number {
  // Use Array.from to properly handle unicode characters including emojis
  return Array.from(str).length;
}

/**
 * Truncate string to a specific visual length, handling emojis properly
 */
function truncateToVisualLength(str: string, targetLength: number): string {
  const chars = Array.from(str);
  return chars.slice(0, targetLength).join('');
}

export default useAddressTag;
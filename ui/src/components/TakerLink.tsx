import React from 'react';
import InternalLink from './InternalLink';
import { formatAddress } from '../lib/utils';
import { useAddressTag } from '../hooks/useAddressTag';

interface TakerLinkProps {
  takerAddress: string;
  chainId?: number;
  showFullAddress?: boolean;
  className?: string;
}

/**
 * Specialized component for taker links that navigates to the TakerDetails page
 * Uses InternalLink with address variant for consistent styling and hover actions
 */
const TakerLink: React.FC<TakerLinkProps> = ({ 
  takerAddress, 
  chainId,
  showFullAddress = false,
  className = ""
}) => {
  const { getDisplayName, getTagInfo } = useAddressTag();
  const tagInfo = getTagInfo(takerAddress);
  const displayText = getDisplayName(takerAddress, {
    showFullAddress,
    addressLength: 5,
    maxTagLength: 9
  });

  return (
    <span className="inline-flex items-center space-x-1">
      <InternalLink
        to={`/taker/${takerAddress}`}
        variant="address"
        address={takerAddress}
        chainId={chainId}
        className={className}
      >
        {displayText}
      </InternalLink>
    </span>
  );
};

export default TakerLink;
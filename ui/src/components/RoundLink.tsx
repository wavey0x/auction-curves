import React from 'react';
import InternalLink from './InternalLink';

interface RoundLinkProps {
  chainId: number;
  auctionAddress: string;
  roundId: number | string;
  className?: string;
}

/**
 * Standardized Round Link component for consistent Round ID display across all tables and pages
 * Uses the same styling as auction addresses (font-mono text-sm)
 */
const RoundLink: React.FC<RoundLinkProps> = ({
  chainId,
  auctionAddress,
  roundId,
  className = '',
}) => {
  return (
    <InternalLink
      to={`/round/${chainId}/${auctionAddress}/${roundId}`}
      variant="round"
      className={`font-mono text-sm ${className}`}
    >
      R{roundId}
    </InternalLink>
  );
};

export default RoundLink;
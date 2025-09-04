import React from "react";
import { cn, formatAddress } from "../lib/utils";
import InternalLink from "./InternalLink";
import ExternalAddressLink from "./ExternalAddressLink";
import { useAddressTag } from "../hooks/useAddressTag";

interface AddressLinkProps {
  address: string;
  chainId: number;
  type?: "auction" | "token" | "address"; // Type determines internal linking
  length?: number;
  className?: string;
  showFullOnHover?: boolean;
}

const AddressLink: React.FC<AddressLinkProps> = ({
  address,
  chainId,
  type = "address",
  length = 5,
  className = "",
  showFullOnHover = true,
}) => {
  const { getDisplayName, getTagInfo } = useAddressTag();
  const tagInfo = getTagInfo(address);
  // Determine internal link based on type
  const getInternalLink = () => {
    switch (type) {
      case "auction":
        return `/auction/${chainId}/${address}`;
      default:
        return null;
    }
  };

  const internalLink = getInternalLink();
  const displayText = getDisplayName(address, {
    showFullAddress: false,
    addressLength: length,
    maxTagLength: 9
  });

  return (
    <div
      className={cn(
        "inline-flex items-center justify-center font-mono text-xs space-x-1",
        className
      )}
    >
      {internalLink ? (
        <InternalLink
          to={internalLink}
          variant="address"
          className="select-all"
          address={address}
          chainId={chainId}
        >
          {displayText}
        </InternalLink>
      ) : (
        <ExternalAddressLink
          address={address}
          chainId={chainId}
          type={type}
          length={length}
          showFullOnHover={showFullOnHover}
          displayText={displayText}
        />
      )}
    </div>
  );
};

export default AddressLink;
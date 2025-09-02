import React from "react";
import { cn, formatAddress } from "../lib/utils";
import InternalLink from "./InternalLink";
import ExternalAddressLink from "./ExternalAddressLink";

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

  return (
    <div
      className={cn(
        "inline-flex items-center justify-center font-mono text-xs",
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
          {formatAddress(address, length)}
        </InternalLink>
      ) : (
        <ExternalAddressLink
          address={address}
          chainId={chainId}
          type={type}
          length={length}
          showFullOnHover={showFullOnHover}
        />
      )}
    </div>
  );
};

export default AddressLink;
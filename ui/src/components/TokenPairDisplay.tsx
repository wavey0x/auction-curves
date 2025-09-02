import React from "react";

interface TokenPairDisplayProps {
  fromToken: string | React.ReactNode;
  toToken: string;
  fromClassName?: string;
  toClassName?: string;
  arrowClassName?: string;
  size?: "sm" | "base";
}

const TokenPairDisplay: React.FC<TokenPairDisplayProps> = ({
  fromToken,
  toToken,
  fromClassName = "text-gray-300",
  toClassName = "text-gray-300", 
  arrowClassName = "text-gray-500",
  size = "sm"
}) => {
  const textSize = size === "sm" ? "text-sm" : "text-base";
  const arrowSize = size === "sm" ? "text-xs" : "text-sm";
  
  return (
    <div className="flex flex-col items-start">
      <div className={`font-medium ${textSize} ${fromClassName} flex items-center space-x-1`}>
        <span>{fromToken}</span>
        <span className={`${arrowSize} ${arrowClassName}`}>→</span>
      </div>
      <div className={`font-bold ${textSize} ${toClassName}`}>
        {toToken}
      </div>
    </div>
  );
};

export default TokenPairDisplay;
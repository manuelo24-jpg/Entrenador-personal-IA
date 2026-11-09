import React from "react";

interface EpiaLogoProps {
  size?: "sm" | "md" | "lg" | "xl";
  className?: string;
}

const SIZE_CLASSES = {
  sm: "w-8 h-8 rounded-lg",
  md: "w-10 h-10 rounded-xl",
  lg: "w-14 h-14 rounded-2xl",
  xl: "w-20 h-20 rounded-3xl",
};

const ICON_SIZES = {
  sm: "w-5 h-5",
  md: "w-6 h-6",
  lg: "w-8 h-8",
  xl: "w-11 h-11",
};

export const EpiaLogo: React.FC<EpiaLogoProps> = ({
  size = "md",
  className = "",
}) => {
  return (
    <div
      className={`${SIZE_CLASSES[size]} bg-gradient-to-br from-epia-500 to-epia-cyan flex items-center justify-center shadow-lg shadow-epia-500/30 shrink-0 ${className}`}
    >
      <svg
        viewBox="0 0 24 24"
        fill="none"
        className={ICON_SIZES[size]}
        stroke="white"
        strokeWidth="2.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
      </svg>
    </div>
  );
};


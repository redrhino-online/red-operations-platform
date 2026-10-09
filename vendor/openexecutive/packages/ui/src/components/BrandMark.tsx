type BrandMarkSize = "sm" | "md" | "lg";

// RED overlay (ADR 0011): the brand mark reads RED, not OE.
const BOX_CLASSES: Record<BrandMarkSize, string> = {
  sm: "w-7 h-7 rounded-lg bg-gradient-to-br from-red-600 to-red-800 flex items-center justify-center shadow-lg shadow-red-600/20",
  md: "w-7 h-7 rounded-full bg-gradient-to-br from-red-600 to-red-800 flex items-center justify-center shadow-lg shadow-red-600/20",
  lg: "w-12 h-12 rounded-2xl bg-gradient-to-br from-red-600 to-red-800 flex items-center justify-center shadow-xl shadow-red-600/25",
};

const TEXT_CLASSES: Record<BrandMarkSize, string> = {
  sm: "text-white text-[10px] tracking-tight font-bold",
  md: "text-white text-[10px] tracking-tight font-semibold",
  lg: "text-white text-base tracking-tight font-bold",
};

interface BrandMarkProps {
  size?: BrandMarkSize;
}

export default function BrandMark({ size = "sm" }: BrandMarkProps) {
  return (
    <div className={BOX_CLASSES[size]} aria-hidden>
      <span className={TEXT_CLASSES[size]}>RED</span>
    </div>
  );
}

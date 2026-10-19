/** Rashomon mark: torii gate as a line drawing (two uprights, curved kasagi lintel, nuki tie-beam). */
export const BRAND_VERMILION = '#B5533F';

export function ToriiMark({ size = 28, strokeWidth = 1.5 }: { size?: number; strokeWidth?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" stroke="currentColor" strokeWidth={strokeWidth}
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
      <path d="M3 7.5c4.5 1.6 21.5 1.6 26 0" />
      <path d="M6 12.5h20" />
      <path d="M9.5 8.6V28M22.5 8.6V28" />
    </svg>
  );
}

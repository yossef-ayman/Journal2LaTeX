import type { ThicknessConfig } from '../types/book';

export const DEFAULT_THICKNESS_CONFIG: ThicknessConfig = {
  minThickness: 12,
  maxThickness: 90,
  thicknessPerPage: 0.14,
};

/**
 * Calculates physical 3D book thickness in pixels based on page count.
 * 
 * Realistic scale:
 * - 50 pages   -> ~14px (Thin booklet)
 * - 150 pages  -> ~21px (Standard book)
 * - 350 pages  -> ~49px (Medium hardcover)
 * - 600 pages  -> ~84px (Thick textbook)
 * - 800+ pages -> Clamped to 90px max (Prevents unrealistic cube distortion)
 */
export function calculateBookThickness(
  pages: number | undefined | null,
  config: Partial<ThicknessConfig> = {}
): number {
  const mergedConfig: ThicknessConfig = {
    ...DEFAULT_THICKNESS_CONFIG,
    ...config,
  };

  if (typeof pages !== 'number' || isNaN(pages) || pages <= 0) {
    return mergedConfig.minThickness;
  }

  const rawThickness = pages * mergedConfig.thicknessPerPage;

  return Math.round(
    Math.min(
      Math.max(rawThickness, mergedConfig.minThickness),
      mergedConfig.maxThickness
    )
  );
}

export const NARRATOR_LAYOUTS = {
  default: {
    right: -12,
    bottom: 0,
    width: 620,
    height: 880,
    scaleBoost: 1
  },
  "thanos": {
    right: -12,
    bottom: 0,
    width: 570,
    height: 780,
    scaleBoost: 0.94
  },
  "reportera_magaly": {
    right: -18,
    bottom: 0,
    width: 560,
    height: 790,
    scaleBoost: 0.92
  },
  "mr_peet": {
    right: -22,
    bottom: 0,
    width: 650,
    height: 760,
    scaleBoost: 0.98
  },
  "gonzalo_nunez": {
    right: -22,
    bottom: 0,
    width: 650,
    height: 760,
    scaleBoost: 0.98
  }
};

export const getNarratorLayout = (name) => {
  const normalized = String(name ?? "")
    .trim()
    .toLowerCase();

  return NARRATOR_LAYOUTS[normalized] ?? NARRATOR_LAYOUTS.default;
};

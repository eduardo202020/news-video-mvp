export const NARRATOR_LAYOUTS = {
  default: {
    right: -12,
    bottom: 0,
    width: 620,
    height: 880,
    scaleBoost: 1
  },
  "cuy-01": {
    right: -26,
    bottom: 0,
    width: 690,
    height: 940,
    scaleBoost: 1.06
  },
  "cuy-02": {
    right: -18,
    bottom: 0,
    width: 560,
    height: 790,
    scaleBoost: 0.92
  },
  "cuy-depor": {
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

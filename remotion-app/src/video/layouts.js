export const NARRATOR_LAYOUTS = {
  default: {
    right: -24,
    bottom: 0,
    width: 620,
    height: 880,
    scaleBoost: 1
  },
  "thanos": {
    right: -24,
    bottom: 0,
    width: 570,
    height: 780,
    scaleBoost: 0.94
  },
  "beto ortiz": {
    right: -24,
    bottom: 0,
    width: 570,
    height: 780,
    scaleBoost: 0.94
  },
  "narrador dbz": {
    right: -24,
    bottom: 0,
    width: 570,
    height: 780,
    scaleBoost: 0.94
  },
  "skipper": {
    right: -24,
    bottom: 0,
    width: 570,
    height: 780,
    scaleBoost: 0.94
  },
  "reportera_magaly": {
    right: -30,
    bottom: 0,
    width: 560,
    height: 790,
    scaleBoost: 0.92
  },
  "reportero panorama": {
    right: -24,
    bottom: 0,
    width: 570,
    height: 780,
    scaleBoost: 0.94
  },
  "mr_peet": {
    right: -24,
    bottom: 0,
    width: 570,
    height: 780,
    scaleBoost: 0.94
  },
  "gonzalo_nunez": {
    right: -48,
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

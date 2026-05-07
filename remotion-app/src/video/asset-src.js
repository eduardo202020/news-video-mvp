export const withAssetVersion = (src, assetVersion) => {
  if (!src) {
    return src;
  }

  if (!assetVersion) {
    return src;
  }

  return src.includes("?") ? `${src}&v=${assetVersion}` : `${src}?v=${assetVersion}`;
};

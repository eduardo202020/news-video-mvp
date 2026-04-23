export const buildSegments = ({segments, newspaperName, coverSrc, text}) => {
  if (segments && segments.length > 0) {
    return segments;
  }

  return [
    {
      newspaperName,
      coverSrc,
      text
    }
  ];
};

export const buildWordHighlights = (caption, progress) => {
  const lines = caption ? caption.split("\n") : [];
  const tokens = [];

  lines.forEach((line, lineIndex) => {
    const words = line.split(" ").filter(Boolean);
    words.forEach((word, wordIndex) => {
      tokens.push({
        key: `${lineIndex}-${wordIndex}-${word}`,
        type: "word",
        text: `${wordIndex > 0 ? " " : ""}${word}`
      });
    });
    if (lineIndex < lines.length - 1) {
      tokens.push({
        key: `break-${lineIndex}`,
        type: "break",
        text: "\n"
      });
    }
  });

  const totalWords = tokens.filter((token) => token.type === "word").length;
  const spokenWords = Math.floor(totalWords * progress);
  let activeWordIndex = 0;

  return tokens.map((token) => {
    if (token.type === "break") {
      return {
        ...token,
        active: false
      };
    }

    const active = activeWordIndex < spokenWords;
    activeWordIndex += 1;
    return {
      ...token,
      active
    };
  });
};

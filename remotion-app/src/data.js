export const stories = {
  comercio: {
    id: "comercio",
    newspaperName: "El Comercio",
    coverSrc: "assets/covers/comercio.webp",
    backgroundSrc: "assets/backgrounds/calle.jpg",
    audioSrc: "assets/audio/comercio_real_v2.wav",
    durationInFrames: 486,
    fps: 30,
    narratorName: "Magaly",
    text: "Portada de El Comercio. La noticia principal resume el cierre de campañas rumbo a Palacio con mítines en Lima y un despliegue de seguridad en todo el país. Este video presenta la recta final electoral con un tono institucional, claro y breve.",
    gestures: [
      "assets/gestures/mascaly-01.png",
      "assets/gestures/mascaly-02.png",
      "assets/gestures/mascaly-03.png",
      "assets/gestures/mascaly-04.png",
      "assets/gestures/mascaly-05.png"
    ]
  },
  trome: {
    id: "trome",
    newspaperName: "Trome",
    coverSrc: "assets/covers/trome.webp",
    backgroundSrc: "assets/backgrounds/calle.jpg",
    audioSrc: "assets/audio/trome_layout_v3.wav",
    durationInFrames: 399,
    fps: 30,
    narratorName: "Magaly",
    text: "Portada de Trome. El titular principal destaca una escalada internacional y el video debe mostrar el periódico en la parte superior mientras la narradora presenta el tema desde abajo con energía y ritmo.",
    gestures: [
      "assets/gestures/mascaly-01.png",
      "assets/gestures/mascaly-02.png",
      "assets/gestures/mascaly-03.png",
      "assets/gestures/mascaly-04.png",
      "assets/gestures/mascaly-05.png"
    ]
  }
};

export const defaultStory = stories.trome;

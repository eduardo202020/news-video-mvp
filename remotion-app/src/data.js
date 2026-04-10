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
      "assets/gestures/magaly/mascaly-01.png",
      "assets/gestures/magaly/mascaly-02.png",
      "assets/gestures/magaly/mascaly-03.png",
      "assets/gestures/magaly/mascaly-04.png",
      "assets/gestures/magaly/mascaly-05.png"
    ]
  },
  trome: {
    id: "trome",
    newspaperName: "Trome",
    coverSrc: "assets/covers/trome.png",
    backgroundSrc: "assets/backgrounds/calle.jpg",
    audioSrc: "assets/audio/trome_es.wav",
    durationInFrames: 201,
    fps: 30,
    narratorName: "Magaly",
    text: "Abrimos con la portada de Trome. El resumen entra con ritmo y prepara el cambio hacia el siguiente diario.",
    gestures: [
      "assets/gestures/magaly/mascaly-01.png",
      "assets/gestures/magaly/mascaly-02.png",
      "assets/gestures/magaly/mascaly-03.png",
      "assets/gestures/magaly/mascaly-04.png",
      "assets/gestures/magaly/mascaly-05.png"
    ]
  },
  ojo: {
    id: "ojo",
    newspaperName: "Ojo",
    coverSrc: "assets/covers/ojo.png",
    backgroundSrc: "assets/backgrounds/calle.jpg",
    audioSrc: "assets/audio/ojo_es.wav",
    durationInFrames: 197,
    fps: 30,
    narratorName: "Fedepico",
    text: "Ahora pasamos a Ojo con un efecto de cambio de pagina para que el recorrido entre periodicos se sienta fluido y real.",
    gestures: [
      "assets/gestures/fedepico/fedepico-01.png",
      "assets/gestures/fedepico/fedepico-02.png",
      "assets/gestures/fedepico/fedepico-03.png",
      "assets/gestures/fedepico/fedepico-04.png",
      "assets/gestures/fedepico/fedepico-05.png",
      "assets/gestures/fedepico/fedepico-06.png"
    ]
  },
  aja: {
    id: "aja",
    newspaperName: "Aja",
    coverSrc: "assets/covers/aja.png",
    backgroundSrc: "assets/backgrounds/calle.jpg",
    audioSrc: "assets/audio/aja_es.wav",
    durationInFrames: 197,
    fps: 30,
    narratorName: "Magaly",
    text: "Cerramos con la portada de Aja para completar la secuencia de diarios con un cambio fluido entre estilos y enfoques.",
    gestures: [
      "assets/gestures/magaly/mascaly-01.png",
      "assets/gestures/magaly/mascaly-02.png",
      "assets/gestures/magaly/mascaly-03.png",
      "assets/gestures/magaly/mascaly-04.png",
      "assets/gestures/magaly/mascaly-05.png"
    ]
  },
  periodicosSecuenciaDemo: {
    id: "periodicos-secuencia-demo",
    newspaperName: "Trome",
    coverSrc: "assets/covers/trome.png",
    backgroundSrc: "assets/backgrounds/calle.jpg",
    audioSrc: "assets/audio/periodicos_secuencia_es.wav",
    durationInFrames: 596,
    fps: 30,
    narratorName: "Magaly",
    text: "Abrimos con la portada de Trome. El resumen entra con ritmo y prepara el cambio hacia el siguiente diario. Ahora pasamos a Ojo con un efecto de cambio de pagina para que el recorrido entre periodicos se sienta fluido y real. Cerramos con la portada de Aja para completar la secuencia de diarios con un cambio fluido entre estilos y enfoques.",
    gestures: [
      "assets/gestures/magaly/mascaly-01.png",
      "assets/gestures/magaly/mascaly-02.png",
      "assets/gestures/magaly/mascaly-03.png",
      "assets/gestures/magaly/mascaly-04.png",
      "assets/gestures/magaly/mascaly-05.png"
    ],
    segments: [
      {
        newspaperName: "Trome",
        coverSrc: "assets/covers/trome.png",
        text: "Abrimos con la portada de Trome. El resumen entra con ritmo y prepara el cambio hacia el siguiente diario.",
        narratorName: "Magaly",
        gestures: [
          "assets/gestures/magaly/mascaly-01.png",
          "assets/gestures/magaly/mascaly-02.png",
          "assets/gestures/magaly/mascaly-03.png",
          "assets/gestures/magaly/mascaly-04.png",
          "assets/gestures/magaly/mascaly-05.png"
        ]
      },
      {
        newspaperName: "Ojo",
        coverSrc: "assets/covers/ojo.png",
        text: "Ahora pasamos a Ojo con un efecto de cambio de pagina para que el recorrido entre periodicos se sienta fluido y real.",
        narratorName: "Fedepico",
        gestures: [
          "assets/gestures/fedepico/fedepico-01.png",
          "assets/gestures/fedepico/fedepico-02.png",
          "assets/gestures/fedepico/fedepico-03.png",
          "assets/gestures/fedepico/fedepico-04.png",
          "assets/gestures/fedepico/fedepico-05.png",
          "assets/gestures/fedepico/fedepico-06.png"
        ]
      },
      {
        newspaperName: "Aja",
        coverSrc: "assets/covers/aja.png",
        text: "Cerramos con la portada de Aja para completar la secuencia de diarios con un cambio fluido entre estilos y enfoques.",
        narratorName: "Magaly",
        gestures: [
          "assets/gestures/magaly/mascaly-01.png",
          "assets/gestures/magaly/mascaly-02.png",
          "assets/gestures/magaly/mascaly-03.png",
          "assets/gestures/magaly/mascaly-04.png",
          "assets/gestures/magaly/mascaly-05.png"
        ]
      }
    ]
  }
};

export const defaultStory = stories.periodicosSecuenciaDemo;

export const stories = {
  comercio: {
    id: "comercio",
    newspaperName: "El Comercio",
    coverSrc: "assets/covers/comercio.webp",
    backgroundSrc: "assets/backgrounds/calle.jpg",
    audioSrc: "assets/audio/comercio_real_v2.wav",
    durationInFrames: 486,
    fps: 30,
    narratorName: "Cuy-01",
    text: "Portada de El Comercio. La noticia principal resume el cierre de campañas rumbo a Palacio con mítines en Lima y un despliegue de seguridad en todo el país. Este video presenta la recta final electoral con un tono institucional, claro y breve.",
    gestures: [
      "assets/gestures/cuy/01/cuy-01.png",
      "assets/gestures/cuy/01/cuy-02.png",
      "assets/gestures/cuy/01/cuy-03.png",
      "assets/gestures/cuy/01/cuy-04.png",
      "assets/gestures/cuy/01/cuy-05.png",
      "assets/gestures/cuy/01/cuy-06.png"
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
    narratorName: "Cuy-01",
    text: "Abrimos con la portada de Trome. El resumen entra con ritmo y prepara el cambio hacia el siguiente diario.",
    gestures: [
      "assets/gestures/cuy/01/cuy-01.png",
      "assets/gestures/cuy/01/cuy-02.png",
      "assets/gestures/cuy/01/cuy-03.png",
      "assets/gestures/cuy/01/cuy-04.png",
      "assets/gestures/cuy/01/cuy-05.png",
      "assets/gestures/cuy/01/cuy-06.png"
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
    narratorName: "Cuy-02",
    text: "Ahora pasamos a Ojo con un efecto de cambio de pagina para que el recorrido entre periodicos se sienta fluido y real.",
    gestures: [
      "assets/gestures/cuy/02/cuyo-01.png",
      "assets/gestures/cuy/02/cuyo-02.png",
      "assets/gestures/cuy/02/cuyo-03.png",
      "assets/gestures/cuy/02/cuyo-04.png",
      "assets/gestures/cuy/02/cuyo-05.png",
      "assets/gestures/cuy/02/cuyo-06.png"
    ]
  },
  libero: {
    id: "libero",
    newspaperName: "Libero",
    coverSrc: "assets/covers/líbero.jpg",
    backgroundSrc: "assets/backgrounds/calle.jpg",
    audioSrc: "assets/audio/libero_es.wav",
    durationInFrames: 196,
    fps: 30,
    narratorName: "Cuy-Depor",
    text: "Cerramos con la portada de Libero junto al cuy deportivo para darle un cierre mas futbolero y energico a la secuencia.",
    gestures: [
      "assets/gestures/cuy/depor/cuydepor-01.png",
      "assets/gestures/cuy/depor/cuydepor-02.png",
      "assets/gestures/cuy/depor/cuydepor-03.png",
      "assets/gestures/cuy/depor/cuydepor-05.png",
      "assets/gestures/cuy/depor/cuydepor-06.png"
    ]
  },
  periodicosSecuenciaDemo: {
    id: "periodicos-secuencia-demo",
    newspaperName: "Trome",
    coverSrc: "assets/covers/trome.png",
    backgroundSrc: "assets/backgrounds/calle.jpg",
    audioSrc: "assets/audio/periodicos_secuencia_es.wav",
    durationInFrames: 594,
    fps: 30,
    narratorName: "Cuy-01",
    text: "Abrimos con la portada de Trome. El resumen entra con ritmo y prepara el cambio hacia el siguiente diario. Ahora pasamos a Ojo con un efecto de cambio de pagina para que el recorrido entre periodicos se sienta fluido y real. Cerramos con la portada de Libero junto al cuy deportivo para darle un cierre mas futbolero y energico a la secuencia.",
    gestures: [
      "assets/gestures/cuy/01/cuy-01.png",
      "assets/gestures/cuy/01/cuy-02.png",
      "assets/gestures/cuy/01/cuy-03.png",
      "assets/gestures/cuy/01/cuy-04.png",
      "assets/gestures/cuy/01/cuy-05.png",
      "assets/gestures/cuy/01/cuy-06.png"
    ],
    segments: [
      {
        newspaperName: "Trome",
        coverSrc: "assets/covers/trome.png",
        text: "Abrimos con la portada de Trome. El resumen entra con ritmo y prepara el cambio hacia el siguiente diario.",
        narratorName: "Cuy-01",
        gestures: [
          "assets/gestures/cuy/01/cuy-01.png",
          "assets/gestures/cuy/01/cuy-02.png",
          "assets/gestures/cuy/01/cuy-03.png",
          "assets/gestures/cuy/01/cuy-04.png",
          "assets/gestures/cuy/01/cuy-05.png",
          "assets/gestures/cuy/01/cuy-06.png"
        ]
      },
      {
        newspaperName: "Ojo",
        coverSrc: "assets/covers/ojo.png",
        text: "Ahora pasamos a Ojo con un efecto de cambio de pagina para que el recorrido entre periodicos se sienta fluido y real.",
        narratorName: "Cuy-02",
        gestures: [
          "assets/gestures/cuy/02/cuyo-01.png",
          "assets/gestures/cuy/02/cuyo-02.png",
          "assets/gestures/cuy/02/cuyo-03.png",
          "assets/gestures/cuy/02/cuyo-04.png",
          "assets/gestures/cuy/02/cuyo-05.png",
          "assets/gestures/cuy/02/cuyo-06.png"
        ]
      },
      {
        newspaperName: "Libero",
        coverSrc: "assets/covers/líbero.jpg",
        text: "Cerramos con la portada de Libero junto al cuy deportivo para darle un cierre mas futbolero y energico a la secuencia.",
        narratorName: "Cuy-Depor",
        gestures: [
          "assets/gestures/cuy/depor/cuydepor-01.png",
          "assets/gestures/cuy/depor/cuydepor-02.png",
          "assets/gestures/cuy/depor/cuydepor-03.png",
          "assets/gestures/cuy/depor/cuydepor-05.png",
          "assets/gestures/cuy/depor/cuydepor-06.png"
        ]
      }
    ]
  }
};

export const defaultStory = stories.periodicosSecuenciaDemo;

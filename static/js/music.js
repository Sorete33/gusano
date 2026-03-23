// Get references to all necessary DOM elements
const playPauseBtn = document.getElementById("playPause");
const prevBtn = document.getElementById("prev");
const nextBtn = document.getElementById("next");
const songListEl = document.getElementById("songList");
const progress = document.getElementById("progress");
const volume = document.getElementById("volume");
const currentTimeEl = document.getElementById("currentTime");
const durationEl = document.getElementById("duration");
const albumArt = document.getElementById("albumArt");
const title = document.getElementById("title");
const artist = document.getElementById("artist");
const playlistBtn = document.getElementById("togglePlaylist");
const playlist = document.getElementById("playlist");
const repeatBtn = document.getElementById("repeatBtn");
const shuffleBtn = document.getElementById("shuffleBtn");
const overlay = document.getElementById("overlay");
const closePlaylist = document.getElementById("closePlaylist");

// State variables
let isPlaying = false;
let currentSongIndex = 0;
let repeatMode = "none";
let shuffledSongs = [];
let isShuffled = false;
// Song data (replace with your actual songs)
const songs = [
  {
    title: "Entrance Festimaga 1",
    artist: "Entrance",
    src: "https://files.catbox.moe/p1lh8s.mp3",
    img: "/covers/festimaga1.jpg",
  },

  {
    title: "Inteligencia Accidental Festimaga 1",
    artist: "Inteligencia Accidental",
    src: "https://files.catbox.moe/xbdnwu.mp3",
    img: "/covers/festimaga1.jpg",
  },

  {
    title: "Parasomnia Festimaga 1",
    artist: "Parasomnia",
    src: "https://files.catbox.moe/cc7crl.mp3",
    img: "/covers/festimaga1.jpg",
  },
  
  {
    title: "Sala Roja Festimaga 1",
    artist: "Sala Roja",
    src: "https://files.catbox.moe/2sab53.mp3",
    img: "/covers/festimaga1.jpg",
  },

  {
    title: "Armando Alonso en Casa Fratello",
    artist: "Armando Alonso",
    src: "https://files.catbox.moe/4icsi1.mp3",
    img: "/covers/fratello.png",
  },

  {
    title: "Los Bad Seed en Sala Biaus",
    artist: " Los Bad Seed",
    src: "https://files.catbox.moe/3l5s6p.mp3",
    img: "/covers/bad-biaus.jpg",
  },

  {
    title: "Yula en Beertonic",
    artist: "Julian Amar",
    src: "https://files.catbox.moe/zn5ybl.mp3",
    img: "/covers/yula.jpg",
  },

  {
    title: "Prima León en el Festival Consciente",
    artist: "Prima León",
    src: "https://files.catbox.moe/wfudnd.mp3",
    img: "/covers/festi-cons1.webp",
  },

  {
    title: "No Soy de Acá en el Festival Consciente",
    artist: "No Soy de Acá",
    src: "https://files.catbox.moe/tyrb3c.mp3",
    img: "/covers/festi-cons1.webp",
  },

  {
    title: "Entrance en el Festival Consciente",
    artist: "Entrance",
    src: "https://files.catbox.moe/hhizka.mp3",
    img: "/covers/festi-cons1.webp",
  },

  {
    title: "Los Pozoz en el Festival Consciente",
    artist: "Los Pozoz",
    src: "https://files.catbox.moe/yf8btq.mp3",
    img: "/covers/festi-cons1.webp",
  },

  {
    title: "Round 2 en el Festival Demolición",
    artist: "Round 2",
    src: "https://files.catbox.moe/lfs2fb.mp3",
    img: "/covers/demo.jpg",
  },

  {
    title: "Entrance en el Festival Demolición",
    artist: "Entrance",
    src: "https://files.catbox.moe/ppua4v.mp3",
    img: "/covers/demo.jpg",
  },

  {
    title: "Sala Roja en el Festival Demolición",
    artist: "Sala Roja",
    src: "https://files.catbox.moe/l8y6z9.mp3",
    img: "/covers/demo.jpg",
  },

  {
    title: "La Vitrola Envenenada en la Ronda de Bandas",
    artist: "La Vitrola Envenenada",
    src: "https://files.catbox.moe/ztn5z0.mp3",
    img: "/covers/ronda1.jpg",
  },

  {
    title: "La Toma de Roma en la Ronda de Bandas",
    artist: "La Toma de Roma",
    src: "https://files.catbox.moe/vvosvl.mp3",
    img: "/covers/ronda1.jpg",
  },

  {
    title: "Entrance en la Ronda de Bandas",
    artist: "Entrance",
    src: "https://files.catbox.moe/yoe2na.mp3",
    img: "/covers/ronda1.jpg",
  },

  {
    title: "Parasomnia en la Ronda de Bandas",
    artist: "Parasomnia",
    src: "https://files.catbox.moe/0fu10z.mp3",
    img: "/covers/ronda1.jpg",
  },

  {
    title: "Juanito Alimaña en Sala Biaus",
    artist: "Juanito Alimaña",
    src: "https://files.catbox.moe/7cihmf.mp3",
    img: "/covers/juanito.jpg",
  },

  {
    title: "Nicolas Muchiut en Sala Biaus",
    artist: "Nicolas Muchiut",
    src: "https://files.catbox.moe/q477ut.mp3",
    img: "/covers/juanito.jpg",
  },

  {
    title: "Ser Sur en Sala Biaus",
    artist: "Ser Sur",
    src: "https://files.catbox.moe/feo7wv.mp3",
    img: "/covers/juanito.jpg",
  },

  {
    title: "Armando Alonso en el Teatro Trac",
    artist: "Armando Alonso, Agustín Barbieri, Nicolas Benagui",
    src: "https://files.catbox.moe/wv8ujs.mp3",
    img: "/covers/armand-trac.png",
  },

  {
    title: "Proyecto Spinetta en el Teatro Trac",
    artist: "Rocío Palazzo, Ignacio Viano, Nicolas Benagui",
    src: "https://files.catbox.moe/i52swa.mp3",
    img: "/covers/spinetta.webp",
  },
  
  {
    title: "Mate Jazz en Beertonic",
    artist: "Mate Jazz",
    src: "https://files.catbox.moe/1qwixg.mp3",
    img: "/covers/mate.jpg",
  },

  {
    title: "Yula y Abril Amar + Invitades en Beertonic ",
    artist: "Yula y Abril Amar",
    src: "https://files.catbox.moe/kh1bf0.mp3",
    img: "/covers/yula.jpg",
  },

  {
    title: "Cumpleaños Accidental en Sala Biaus",
    artist: "Inteligencia Accidental",
    src: "https://files.catbox.moe/l50rmt.mp3",
    img: "/covers/cumple-acc.jpg",
  },

  {
    title: "Ronda Catonga en el cumple de La Ronda",
    artist: "Ronda Catonga",
    src: "https://files.catbox.moe/7suvnz.mp3",
    img: "/covers/cumple-ron.jpg",
  },

  {
    title: "Catango Trío en el cumple de La Ronda",
    artist: "Catango Trío",
    src: "https://files.catbox.moe/z143qt.mp3",
    img: "/covers/cumple-ron.jpg",
  },

  {
    title: "Roco y los Chaks en el cumple de La Ronda",
    artist: "Roco y los Chaks",
    src: "https://files.catbox.moe/to2xy0.mp3",
    img: "/covers/cumple-ron.jpg",
  },

  {
    title: "Epifanicas en el cumple de La Ronda",
    artist: "Epifanicas",
    src: "https://files.catbox.moe/paf97s.mp3",
    img: "/covers/cumple-ron.jpg",
  },

  {
    title: "Telar en Beertonic",
    artist: "Telar",
    src: "https://files.catbox.moe/ur2qo6.mp3",
    img: "/covers/telar.png",
  },

  {
    title: "Casco y Guada en Grey Bar",
    artist: "Casco y Guada",
    src: "https://files.catbox.moe/xyj9u4.mp3",
    img: "/covers/cascoguada.png",
  },

  {
    title: "Jane Doe en Ricón",
    artist: "Jane Doe",
    src: "https://files.catbox.moe/aqajnb.mp3",
    img: "/covers/jane.jpg",
  },

  {
    title: "Armando Alonso en Beertonic",
    artist: "Armando Alonso, Agustín Barbieri, Nicolas Benaghi",
    src: "https://files.catbox.moe/nnubmi.mp3",
    img: "/covers/armand-beer.png",
  },

  {
    title: "Tigran Hamasyan en el Teatro Coliseo",
    artist: "Tigran Hamasyan",
    src: "https://files.catbox.moe/ypys3b.mp3",
    img: "/covers/tigran.jpg",
  },

  {
    title: " Paez de a dos desde el Teatro Trac ",
    artist: "Nico Muchiut y Fede Ratto",
    src: "https://files.catbox.moe/chl3gs.mp3",
    img: "/covers/paez.jpg",
  },

  {
    title: "Inteligencia Accidental en la Ronda de Bandas",
    artist: "Inteligencia Accidental",
    src: "https://files.catbox.moe/edswyr.mp3",
    img: "/covers/ronda2.jpg",
  },

  {
    title: "Base en la Ronda de Bandas",
    artist: "Base",
    src: "https://files.catbox.moe/fc14c0.mp3",
    img: "/covers/ronda2.jpg",
  },

  {
    title: "Sala Roja en la Ronda de Bandas",
    artist: "Sala Roja",
    src: "https://files.catbox.moe/7mai6b.mp3",
    img: "/covers/ronda2.jpg",
  },

  {
    title: "Inteligencia Accidental en el cumple de Lucas",
    artist: "Inteligencia Accidental",
    src: "https://files.catbox.moe/1y3q74.mp3",
    img: "/covers/cumple-lu.jpg",
  },

  {
    title: "Sala Roja en el cumple de Lucas",
    artist: "Sala Roja",
    src: "https://files.catbox.moe/w5yfc2.mp3",
    img: "/covers/cumple-lu.jpg",
  },

  {
    title: "El Ensamble de música contemporánea interpreta a Philip Glass en el Conservatorio Alberto Williams",
    artist: "El Ensamble de música contemporánea",
    src: "https://files.catbox.moe/lg93s3.mp3",
    img: "/covers/glass.jpg",
  },

  {
    title: "Alumnes del Conservatorio Alberto Williams interpretan y Terry Riley a cargo del profesor Pablo Torre ",
    artist: "Alumnes del Conservatorio Alberto Williams",
    src: "https://files.catbox.moe/mwxfv1.mp3",
    img: "/covers/glass.jpg",
  },

  {
    title: "Epifanicas en Garage Avispa",
    artist: "Epifanicas",
    src: "https://files.catbox.moe/2u4twa.mp3",
    img: "/covers/garage.jpg",
  },

  {
    title: "La Ronda Catonga en la Plaza Venezuela",
    artist: "Ronda Catonga",
    src: "https://files.catbox.moe/gy5zk8.mp3",
    img: "/covers/catonga.jpg",
  },

  {
    title: "Fango y Perlas en Beertonic",
    artist: "Fango y Perlas",
    src: "https://files.catbox.moe/e79q6c.mp3",
    img: "/covers/fango.webp",
  },

  {
    title: "Nómada en la Festimaga",
    artist: "Nómada",
    src: "https://files.catbox.moe/a7wcqy.mp3",
    img: "/covers/festimaga2.png",
  },

  {
    title: "Sala Roja en la Festimaga",
    artist: "Sala Roja",
    src: "https://files.catbox.moe/dyjyrz.mp3",
    img: "/covers/festimaga2.png",
  },

  {
    title: "Entrance en la Festimaga ",
    artist: "Entrance",
    src: "https://files.catbox.moe/uh6yu2.mp3",
    img: "/covers/festimaga2.png",
  },

  {
    title: "Epifanicas en Grey Bar",
    artist: "Epifanicas",
    src: "https://files.catbox.moe/8nzb96.mp3",
    img: "/covers/epis-grey.jpg",
  },

  {
    title: "Valkirias en la Plaza Charo Latessa",
    artist: "Valkirias",
    src: "https://files.catbox.moe/nkrss1.mp3",
    img: "/covers/charo.webp",
  },

  {
    title: "Epifanicas en la Fiesta de la Cebada",
    artist: "Epifanicas",
    src: "https://files.catbox.moe/b594ma.mp3",
    img: "/covers/epis-cebada.jpg",
  },

  {
    title: "Maquinaria Divina en el Festival Consciente",
    artist: "Maquinaria Divina",
    src: "https://files.catbox.moe/oh2itu.mp3",
    img: "/covers/festi-cons2.webp",
  },

  {
    title: "Jane Doe en el Festival Consciente",
    artist: "Jane Doe",
    src: "https://files.catbox.moe/o1nk8u.mp3",
    img: "/covers/festi-cons2.webp",
  },

  {
    title: "Base en el Festival Consciente",
    artist: "Base",
    src: "https://files.catbox.moe/q0qqq6.mp3",
    img: "/covers/festi-cons2.webp",
  },

  {
    title: "Sociedad Macabra en el Festival Consciente",
    artist: "Sociedad Macabra",
    src: "https://files.catbox.moe/6um5nk.mp3",
    img: "/covers/festi-cons2.webp",
  },

  {
    title: "Inteligencia Accidental en el Festival Consciente",
    artist: "Inteligencia Accidental",
    src: "https://files.catbox.moe/kpb3y2.mp3",
    img: "/covers/festi-cons2.webp",
  },

  {
    title: "Forrxs en el Festival Consciente",
    artist: "Forrxs",
    src: "https://files.catbox.moe/fw8fd9.mp3",
    img: "/covers/festi-cons2.webp",
  },

  {
    title: "Guada y Abril dúo en el aniversario de Beertonic (extracto).",
    artist: "Guada y Abril",
    src: "https://files.catbox.moe/4jor73.mp3",
    img: "/covers/cumple-beer.jpg",
  },

  {
    title: "Catango Trío en el aniversario de Beertonic",
    artist: "Catango Trío ",
    src: "https://files.catbox.moe/o9yf05.mp3",
    img: "/covers/cumple-beer.jpg",
  },

  {
    title: "Paprika's Band en el aniversario de Beertonic",
    artist: "Paprika's Band",
    src: "https://files.catbox.moe/k000p1.mp3",
    img: "/covers/cumple-beer.jpg",
  },

  {
    title: "Los Pozoz en la Festimaga ",
    artist: "Los Pozoz",
    src: "https://files.catbox.moe/f0vb1d.mp3",
    img: "/covers/festimaga3.jpg",
  },

  {
    title: "Traumas de la Infancia en la Festimaga",
    artist: "Traumas de la Infancia",
    src: "https://files.catbox.moe/s8qfqf.mp3",
    img: "/covers/festimaga3.jpg",
  },

  {
    title: "Reunión de Traumas interpretando Desahogo en la Festimaga",
    artist: "Yanqui, Nicanor, Chiquilin Sanchez y Simón (el cantor)",
    src: "https://files.catbox.moe/a08fm2.mp3",
    img: "/covers/festimaga3.jpg",
  },

  {
    title: "Base en el Festival Distorsivo",
    artist: "Base",
    src: "https://files.catbox.moe/8blvc7.mp3",
    img: "/covers/festi-distor.webp",
  },

  {
    title: "Entrance en el Festival Distorsivo",
    artist: "Entrance",
    src: "https://files.catbox.moe/y1rcv1.mp3",
    img: "/covers/festi-distor.webp",
  },

  {
    title: "Muestra fin de ciclo de la NUEVA (escuela de) MÚSICA día 1",
    artist: "Nueva Escuela de Música",
    src: "https://files.catbox.moe/sg11i3.mp3",
    img: "/covers/nueva.jpg",
  },

  {
    title: "Muestra fin de ciclo de la NUEVA (escuela de) MÚSICA día 2",
    artist: "Nueva Escuela de Música",
    src: "https://files.catbox.moe/llvbhj.mp3",
    img: "/covers/nueva.jpg",
  },

  {
    title: "Los Pozoz en el Mad Monky Fest",
    artist: "Los Pozoz",
    src: "https://files.catbox.moe/3g4um0.mp3",
    img: "/covers/mad.webp",
  },

  {
    title: "Nómada en el Mad Monky Fest",
    artist: "Nómada",
    src: "https://files.catbox.moe/dcp23i.mp3",
    img: "/covers/mad.webp",
  },

  {
    title: "Sociedad Macabra en el Mad Monky Fest",
    artist: "Sociedad Macabra",
    src: "https://files.catbox.moe/slx3uw.mp3",
    img: "/covers/mad.webp",
  },

  {
    title: "Parasomnia en el Mad Monky Fest",
    artist: "Parasomnia",
    src: "https://files.catbox.moe/1l50w5.mp3",
    img: "/covers/mad.webp",
  },

  {
    title: "Epifanicas Bloque 1 en Sala Biaus",
    artist: "Epifanicas",
    src: "https://files.catbox.moe/51g1x3.mp3",
    img: "/covers/epi-biaus.jpg",
  },

  {
    title: "Hernán de Bragado en Sala Biaus",
    artist: "Hernán de Bragado",
    src: "https://files.catbox.moe/dcs0qf.mp3",
    img: "/covers/epi-biaus.jpg",
  },

  {
    title: "Epifanicas Bloque 2 en Sala Biaus",
    artist: "Epifanicas",
    src: "https://files.catbox.moe/mqcg8y.mp3",
    img: "/covers/epi-biaus.jpg",
  },

  {
    title: "Drama en Sala Biaus",
    artist: "Drama",
    src: "https://files.catbox.moe/u87zop.mp3",
    img: "/covers/bad-drama.jpg",
  },

  {
    title: "Los Bad Seed en Sala Biaus",
    artist: "Los Bad Seed",
    src: "https://files.catbox.moe/1q21vg.mp3",
    img: "/covers/bad-drama.jpg",
  },
  
  {
    title: "Sociedad Macabra en año nuevo fest",
    artist: "Sociedad Macabra",
    src: "https://files.catbox.moe/nz514m.mp3",
    img: "/covers/año.png",
  },
    
  {
    title: "Parasomnia en año nuevo fest",
    artist: "Parasomnia",
    src: "https://files.catbox.moe/a6e37m.mp3",
    img: "/covers/año.png",
  },
    
  {
    title: "IA en año nuevo fest",
    artist: "Inteligencia Accidental",
    src: "https://files.catbox.moe/i60k6t.mp3",
    img: "/covers/año.png",
  }, 
    
  {
    title: "Los Bad Seed en año nuevo fest",
    artist: "Los Bad Seed",
    src: "https://files.catbox.moe/hgf90e.mp3",
    img: "/covers/año.png",
  },
    

  {
    title: "Epifanicas en Encuentro por las Artes",
    artist: "Epifanicas",
    src: "https://files.catbox.moe/3rjs9s.mp3",
    img: "/covers/epi-roco-sun.jpg",
  },


  {
    title: "Sunglasses en Encuentro por las Artes",
    artist: "Sunglasses",
    src: "https://files.catbox.moe/ooo8y2.mp3",
    img: "/covers/epi-roco-sun.jpg",
  },

  
  {
    title: "Roco y los Chacks en Encuentro por las Artes",
    artist: "Roco y los Chacks",
    src: "https://files.catbox.moe/xkdrvl.mp3",
    img: "/covers/epi-roco-sun.jpg",
  },

  {
    title: "Cínica en Sala Biaus",
    artist: "Cínica",
    src: "https://files.catbox.moe/uhjd18.mp3",
    img: "/covers/biaus-cin-ia-mr-nomad.jpg",
  },

  {
    title: "Inteligencia Accidental en Sala Biaus 16-01-26",
    artist: "Inteligencia Accidental",
    src: "https://files.catbox.moe/gulf4e.mp3",
    img: "/covers/biaus-cin-ia-mr-nomad.jpg",
  },

  {
    title: "Sr Wilson en Sala Biaus",
    artist: "Sr Wilson",
    src: "https://files.catbox.moe/8t1ot8.mp3",
    img: "/covers/biaus-cin-ia-mr-nomad.jpg",
  },

  {
    title: "Nómada en Sala Biaus",
    artist: "Nómada",
    src: "https://files.catbox.moe/uvw3ce.mp3",
    img: "/covers/biaus-cin-ia-mr-nomad.jpg",
  },

  {
    title: "Homenaje a El Kuelgue",
    artist: "Kuelguero's band",
    src: "https://files.catbox.moe/9j5gxa.mp3",
    img: "/recitales/ruta30/kuelgue/featured.png",
  },

  {
    title: "Oesterheld en Sala Biaus",
    artist: "Oesterheld",
    src: "https://files.catbox.moe/4wzf3v.mp3",
    img: "/recitales/sala-biaus/oesterheld/featured.jpg",
  },

  {
    title: "Nómada en Galpón Beer",
    artist: "Nómada",
    src: "/audio/galpon/nomada.mp3",
    img: "/covers/nomad-cala-down.jpg",
  },

  {
    title: "San Calavera en Galpón Beer",
    artist: "San Calavera",
    src: "/audio/galpon/calavera.mp3",
    img: "/covers/nomad-cala-down.jpg",
  },

  {
    title: "Downfall en Galpón Beer",
    artist: "Downfall",
    src: "/audio/galpon/downfall.mp3",
    img: "/covers/nomad-cala-down.jpg",
  },

  {
    title: "Epifanicas en Lap Cantina",
    artist: "Epifanicas",
    src: "https://files.catbox.moe/bow1th.mp3",
    img: "/recitales/lap-cantina/epifanicas/featured.jpg",
  },


  {
    title: "Oesterheld en Ruta 30",
    artist: "Oesterheld",
    src: "https://files.catbox.moe/qhrn7g.mp3",
    img: "/recitales/ruta30/oesterheld/featured.jpg",
  },

  {
    title: "Entrance en Sala Biaus",
    artist: "Entrance",
    src: "https://files.catbox.moe/iafe6j.mp3",
    img: "/covers/entrance-ia-sabo-biaus.png",
  },

  {
    title: "Inteligencia Accidental en Sala Biaus",
    artist: "Inteligencia Accidental",
    src: "https://files.catbox.moe/36tdec.mp3",
    img: "/covers/entrance-ia-sabo-biaus.png",
  },

  {
    title: "Sabotaje en Sala Biaus",
    artist: "Sabotaje",
    src: "https://files.catbox.moe/bvkj6x.mp3",
    img: "/covers/entrance-ia-sabo-biaus.png",
  },

  {
    title: "Cinica en Encuentro por las Artes",
    artist: "Cinica",
    src: "https://files.catbox.moe/mcigps.mp3",
    img: "/covers/anticover13.png",
  },

  {
    title: "Facu Dovidio en Encuentro por las Artes",
    artist: "Facu Dovidio",
    src: "https://files.catbox.moe/n29flz.mp3",
    img: "/covers/anticover13.png",
  },

  {
    title: "Paprika's Band en Encuentro por las Artes",
    artist: "Paprika's Band",
    src: "https://files.catbox.moe/6jr85k.mp3",
    img: "/covers/anticover13.png",
  },

  {
    title: "SOFA en Beertonic",
    artist: "SOFA",
    src: "https://files.catbox.moe/rqmo87.mp3",
    img: "/covers/sofa.png",
  },

  {
    title: "Fronda y Raíz en la Varela",
    artist: "Fronda y Raíz",
    src: "https://files.catbox.moe/haq3r8.mp3",
    img: "/covers/raiz.jpg",
  },

  {
    title: "Juanito Alimaña en Encuentro por las Artes",
    artist: "Juanito Alimaña",
    src: "https://files.catbox.moe/pmd0a9.mp3",
    img: "/covers/juanito.jpg",
  },
  
  {
    title: "Paprika's Band en Encuentro por las Artes",
    artist: "Paprika's Band",
    src: "https://files.catbox.moe/npl2es.mp3",
    img: "/covers/juanito.jpg",
  },
  
  {
    title: "Muchiut y los monjes del dudaismo en Encuentro por las Artes",
    artist: "Muchiut y los monjes del dudaismo",
    src: "https://files.catbox.moe/txexq5.mp3",
    img: "/covers/juanito.jpg",
  },

  {
    title: "Rey Midas en Club Conjura",
    artist: "Rey Midas",
    src: "/audio/conjura/Rey-Midas-28-2-26.mp3",
    img: "/covers/seed-capi.jpg",
  },

  {
    title: "Ayende en Club Conjura",
    artist: "Ayende",
    src: "/audio/conjura/Ayende-28-2-26.mp3",
    img: "/covers/seed-capi.jpg",
  },

  {
    title: "VIK en Club Conjura",
    artist: "VIK",
    src: "/audio/conjura/VIK-28-2-26.mp3",
    img: "/covers/seed-capi.jpg",
  },

  {
    title: "Velvet en Club Conjura",
    artist: "Velvet",
    src: "/audio/conjura/Velvet-28-2-26.mp3",
    img: "/covers/seed-capi.jpg",
  },

  {
    title: "Nancy desde el Tren Sarmiento",
    artist: "Nancy",
    src: "https://files.catbox.moe/kswukp.mp3",
    img: "/recitales/tren/nancy/featured.png",
  },

  
  {
    title: "Armando Alonso Trío en Sala Belgrano",
    artist: "Armando Alonso",
    src: "https://files.catbox.moe/didtx2.mp3",
    img: "/recitales/sala-belgrano/armando/featured.jpg",
  },

  
  {
    title: "Base en Sala Biaus",
    artist: "Base",
    src: "https://files.catbox.moe/1jjkyb.mp3",
    img: "/covers/corpo.jpg",
  },

  {
    title: "Ismael es de verdad en Sala Biaus",
    artist: "Ismael es de verdad",
    src: "https://files.catbox.moe/y5fhfz.mp3",
    img: "/covers/corpo.jpg",
  },

  {
    title: "Corpo Porco en Sala Biaus",
    artist: "Corpo Porco",
    src: "https://files.catbox.moe/ts1yj4.mp3",
    img: "/covers/corpo.jpg",
  },

  {
    title: "Sabotage en El Portal del Tango",
    artist: "Sabotage",
    src: "https://files.catbox.moe/59gial.mp3",
    img: "/recitales/el-portal-del-tango/sabotage/featured.jpg",

  },

  {
    title: "Armando Alonso en Beertonic 20-3-26",
    artist: "Armando Alonso",
    src: "https://files.catbox.moe/arm4rw.mp3",
    img: "/recitales/beertonic/armand2/featured.png",

  },
];


const audio = new Audio();

function populateSongList() {
  songListEl.innerHTML = "";
  songs.forEach((song, index) => {
    const li = document.createElement("li");
    li.dataset.index = index;
    li.innerHTML = `
      <span>${song.title} - ${song.artist}</span>
      <span class="song-duration"></span>
    `;
    songListEl.appendChild(li);

    const tempAudio = new Audio(song.src);
    tempAudio.onloadedmetadata = () => {
      li.querySelector('.song-duration').textContent = formatTime(tempAudio.duration);
    };
    tempAudio.onerror = () => {
      li.querySelector('.song-duration').textContent = "Error";
    };
  });
}

function loadSong(index) {
  const song = songs[index];
  title.textContent = song.title || "Unknown Title";
  artist.textContent = song.artist || "Unknown Artist";
  
  albumArt.src = song.img || 'images/default.jpg';
  albumArt.onerror = function() {
    this.onerror = null;
    this.src = 'https://placehold.co/250x250/333333/FFFFFF?text=No+Art';
  };
  
  audio.src = song.src;

  // Update active song in playlist
  songListEl.querySelectorAll("li").forEach((item, i) => {
    item.classList.toggle("active", i === index);
  });

  // Reset UI
  progress.value = 0;
  if (isPlaying) {
    audio.play();
    playPauseBtn.textContent = "pause";
    albumArt.classList.add('playing');
  } else {
    audio.pause();
    playPauseBtn.textContent = "play_arrow";
    albumArt.classList.remove('playing');
  }
}

// Initial load
populateSongList();
loadSong(currentSongIndex);

// === EVENT LISTENERS ===

// Function to close playlist
const closeDrawer = () => {
  playlist.classList.remove("show");
  overlay.classList.remove("active");
};

playPauseBtn.onclick = () => {
  if (isPlaying) {
    audio.pause();
    playPauseBtn.textContent = "play_arrow";
    albumArt.classList.remove('playing');
  } else {
    audio.play();
    playPauseBtn.textContent = "pause";
    albumArt.classList.add('playing');
  }
  isPlaying = !isPlaying;
};

prevBtn.onclick = () => {
  if (isShuffled && shuffledSongs.length > 0) {
    let currentShuffledIndex = shuffledSongs.indexOf(currentSongIndex);
    currentShuffledIndex = (currentShuffledIndex - 1 + shuffledSongs.length) % shuffledSongs.length;
    currentSongIndex = shuffledSongs[currentShuffledIndex];
  } else {
    currentSongIndex = (currentSongIndex - 1 + songs.length) % songs.length;
  }
  loadSong(currentSongIndex);
  audio.play();
  isPlaying = true;
};

nextBtn.onclick = () => {
  if (isShuffled && shuffledSongs.length > 0) {
    let currentShuffledIndex = shuffledSongs.indexOf(currentSongIndex);
    currentShuffledIndex = (currentShuffledIndex + 1) % shuffledSongs.length;
    currentSongIndex = shuffledSongs[currentShuffledIndex];
  } else {
    currentSongIndex = (currentSongIndex + 1) % songs.length;
  }
  loadSong(currentSongIndex);
  audio.play();
  isPlaying = true;
};

songListEl.onclick = (e) => {
  let targetLi = e.target.closest("li");
  if (targetLi && targetLi.dataset.index !== undefined) {
    currentSongIndex = parseInt(targetLi.dataset.index);
    loadSong(currentSongIndex);
    audio.play();
    isPlaying = true;

    // AUTO-CLOSE: This hides the drawer after picking a song.
    // On desktop, this has no effect because the sidebar is fixed by CSS.
    closeDrawer(); 
  }
};

// 👉 NEW: Tap-to-seek on progress bar (great for mobile!)
progress.addEventListener('click', (e) => {
  const rect = progress.getBoundingClientRect();
  const pos = (e.clientX - rect.left) / rect.width;
  if (!isNaN(audio.duration)) {
    audio.currentTime = pos * audio.duration;
  }
});

// Progress update
audio.ontimeupdate = () => {
  if (audio.duration) {
    progress.value = (audio.currentTime / audio.duration) * 100;
    currentTimeEl.textContent = formatTime(audio.currentTime);
  }
};

audio.onloadedmetadata = () => {
  durationEl.textContent = formatTime(audio.duration);
};

// Volume
volume.oninput = () => {
  audio.volume = volume.value;
};


// Repeat logic
audio.onended = () => {
  if (repeatMode === "one") {
    audio.currentTime = 0;
    audio.play();
  } else if (repeatMode === "all") {
    nextBtn.click();
  } else {
    if (currentSongIndex === songs.length - 1 && !isShuffled) {
      isPlaying = false;
      playPauseBtn.textContent = "play_arrow";
      albumArt.classList.remove('playing');
      audio.pause();
      audio.currentTime = 0;
    } else {
      nextBtn.click();
    }
  }
};

repeatBtn.onclick = () => {
  if (repeatMode === "none") {
    repeatMode = "one";
    repeatBtn.textContent = "repeat_one";
  } else if (repeatMode === "one") {
    repeatMode = "all";
    repeatBtn.textContent = "repeat";
  } else {
    repeatMode = "none";
    repeatBtn.textContent = "repeat";
  }
  repeatBtn.style.color = repeatMode === "none" ? "#fff" : "#1db954";
};

shuffleBtn.onclick = () => {
  isShuffled = !isShuffled;
  shuffleBtn.style.color = isShuffled ? "#1db954" : "#fff";

  if (isShuffled) {
    shuffledSongs = shuffleArray([...Array(songs.length).keys()]);
    const idx = shuffledSongs.indexOf(currentSongIndex);
    if (idx > -1) shuffledSongs.splice(idx, 1);
    shuffledSongs.unshift(currentSongIndex);
  } else {
    shuffledSongs = [];
  }
};

// Utilities
function shuffleArray(array) {
  for (let i = array.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [array[i], array[j]] = [array[j], array[i]];
  }
  return array;
}

function formatTime(sec) {
  if (isNaN(sec) || sec < 0) return "0:00";
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}

audio.onerror = () => {
  console.error("Audio load error:", audio.error);
  playPauseBtn.textContent = "play_arrow";
  albumArt.classList.remove('playing');
  isPlaying = false;
};

volume.value = audio.volume;

// Function to open playlist
playlistBtn.onclick = () => {
  playlist.classList.add("show");
  overlay.classList.add("active");
};



// Function to open playlist
playlistBtn.onclick = () => {
  playlist.classList.add("show");
  overlay.classList.add("active");
};

// Close logic for the "X" button and the background overlay
closePlaylist.onclick = closeDrawer;
overlay.onclick = closeDrawer;
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
const viewToggle = document.getElementById("viewToggle");
const coverGrid = document.getElementById("coverGrid");
const overlay = document.getElementById("overlay");
const closePlaylist = document.getElementById("closePlaylist");

// State variables
let isPlaying = false;
let currentSongIndex = 0;
let repeatMode = "none";
let shuffledSongs = [];
let isShuffled = false;
let viewMode = "list";
// Song data (replace with your actual songs)
const songs = [
  {
    title: "Entrance Festimaga 1",
    artist: "Entrance",
    src: "https://files.catbox.moe/p1lh8s.mp3",
    img: "/covers/festimaga1.jpg",
    date: "2025-04-04",
  },

  {
    title: "Inteligencia Accidental Festimaga 1",
    artist: "Inteligencia Accidental",
    src: "https://files.catbox.moe/xbdnwu.mp3",
    img: "/covers/festimaga1.jpg",
    date: "2025-04-04",

  },

  {
    title: "Parasomnia Festimaga 1",
    artist: "Parasomnia",
    src: "https://files.catbox.moe/cc7crl.mp3",
    img: "/covers/festimaga1.jpg",
    date: "2025-04-04",
  },

  {
    title: "Sala Roja Festimaga 1",
    artist: "Sala Roja",
    src: "https://files.catbox.moe/2sab53.mp3",
    img: "/covers/festimaga1.jpg",
    date: "2025-04-04",
  },

  {
    title: "Armando Alonso en Casa Fratello",
    artist: "Armando Alonso",
    src: "https://files.catbox.moe/4icsi1.mp3",
    img: "/covers/fratello.png",
    date: "2025-04-26",
  },

  {
    title: "Los Bad Seed en Sala Biaus",
    artist: " Los Bad Seed",
    src: "https://files.catbox.moe/3l5s6p.mp3",
    img: "/covers/bad-biaus.jpg",
    date: "2025-05-09",
  },

  {
    title: "Yula en Beertonic",
    artist: "Julian Amar",
    src: "https://files.catbox.moe/zn5ybl.mp3",
    img: "/covers/yula.jpg",
    date: "2025-05-04",
  },

  {
    title: "Prima León en el Festival Consciente",
    artist: "Prima León",
    src: "https://files.catbox.moe/wfudnd.mp3",
    img: "/covers/festi-cons1.webp",
    date: "2025-04-19",
  },

  {
    title: "No Soy de Acá en el Festival Consciente",
    artist: "No Soy de Acá",
    src: "https://files.catbox.moe/tyrb3c.mp3",
    img: "/covers/festi-cons1.webp",
    date: "2025-04-19",
  },

  {
    title: "Entrance en el Festival Consciente",
    artist: "Entrance",
    src: "https://files.catbox.moe/hhizka.mp3",
    img: "/covers/festi-cons1.webp",
    date: "2025-04-19",
  },

  {
    title: "Los Pozoz en el Festival Consciente",
    artist: "Los Pozoz",
    src: "https://files.catbox.moe/yf8btq.mp3",
    img: "/covers/festi-cons1.webp",
    date: "2025-04-19",
  },

  {
    title: "Round 2 en el Festival Demolición",
    artist: "Round 2",
    src: "https://files.catbox.moe/lfs2fb.mp3",
    img: "/covers/demo.jpg",
    date: "2025-06-28",
  },

  {
    title: "Entrance en el Festival Demolición",
    artist: "Entrance",
    src: "https://files.catbox.moe/ppua4v.mp3",
    img: "/covers/demo.jpg",
    date: "2025-06-28",
  },

  {
    title: "Sala Roja en el Festival Demolición",
    artist: "Sala Roja",
    src: "https://files.catbox.moe/l8y6z9.mp3",
    img: "/covers/demo.jpg",
    date: "2025-06-28",
  },

  {
    title: "La Vitrola Envenenada en la Ronda de Bandas",
    artist: "La Vitrola Envenenada",
    src: "https://files.catbox.moe/ztn5z0.mp3",
    img: "/covers/ronda1.jpg",
    date: "2025-07-12",
  },

  {
    title: "La Toma de Roma en la Ronda de Bandas",
    artist: "La Toma de Roma",
    src: "https://files.catbox.moe/vvosvl.mp3",
    img: "/covers/ronda1.jpg",
    date: "2025-07-12",
  },

  {
    title: "Entrance en la Ronda de Bandas",
    artist: "Entrance",
    src: "https://files.catbox.moe/yoe2na.mp3",
    img: "/covers/ronda1.jpg",
    date: "2025-07-12",
  },

  {
    title: "Parasomnia en la Ronda de Bandas",
    artist: "Parasomnia",
    src: "https://files.catbox.moe/0fu10z.mp3",
    img: "/covers/ronda1.jpg",
    date: "2025-07-12",
  },

  {
    title: "Juanito Alimaña en Sala Biaus",
    artist: "Juanito Alimaña",
    src: "https://files.catbox.moe/7cihmf.mp3",
    img: "/covers/juanito.jpg",
    date: "2025-08-09",
  },

  {
    title: "Nicolas Muchiut en Sala Biaus",
    artist: "Nicolas Muchiut",
    src: "https://files.catbox.moe/q477ut.mp3",
    img: "/covers/juanito.jpg",
    date: "2025-08-09",
  },

  {
    title: "Ser Sur en Sala Biaus",
    artist: "Ser Sur",
    src: "https://files.catbox.moe/feo7wv.mp3",
    img: "/covers/juanito.jpg",
    date: "2025-08-09",
  },

  {
    title: "Armando Alonso en el Teatro Trac",
    artist: "Armando Alonso, Agustín Barbieri, Nicolas Benagui",
    src: "https://files.catbox.moe/wv8ujs.mp3",
    img: "/covers/armand-trac.png",
    date: "2025-09-09",
  },

  {
    title: "Proyecto Spinetta en el Teatro Trac",
    artist: "Rocío Palazzo, Ignacio Viano, Nicolas Benagui",
    src: "https://files.catbox.moe/i52swa.mp3",
    img: "/covers/spinetta.webp",
    date: "2025-09-12",
  },

  {
    title: "Mate Jazz en Beertonic",
    artist: "Mate Jazz",
    src: "https://files.catbox.moe/1qwixg.mp3",
    img: "/covers/mate.jpg",
    date: "2025-09-12",
  },

  {
    title: "Yula y Abril Amar + Invitades en Beertonic ",
    artist: "Yula y Abril Amar",
    src: "https://files.catbox.moe/kh1bf0.mp3",
    img: "/covers/yula.jpg",
    date: "2025-09-15",
  },

  {
    title: "Cumpleaños Accidental en Sala Biaus",
    artist: "Inteligencia Accidental",
    src: "https://files.catbox.moe/l50rmt.mp3",
    img: "/covers/cumple-acc.jpg",
    date: "2025-09-19",
  },

  {
    title: "Ronda Catonga en el cumple de La Ronda",
    artist: "Ronda Catonga",
    src: "https://files.catbox.moe/7suvnz.mp3",
    img: "/covers/cumple-ron.jpg",
    date: "2025-09-20",
  },

  {
    title: "Catango Trío en el cumple de La Ronda",
    artist: "Catango Trío",
    src: "https://files.catbox.moe/z143qt.mp3",
    img: "/covers/cumple-ron.jpg",
    date: "2025-09-20",
  },

  {
    title: "Roco y los Chaks en el cumple de La Ronda",
    artist: "Roco y los Chaks",
    src: "https://files.catbox.moe/to2xy0.mp3",
    img: "/covers/cumple-ron.jpg",
    date: "2025-09-20",
  },

  {
    title: "Epifanicas en el cumple de La Ronda",
    artist: "Epifanicas",
    src: "https://files.catbox.moe/paf97s.mp3",
    img: "/covers/cumple-ron.jpg",
    date: "2025-09-20",
  },

  {
    title: "Telar en Beertonic",
    artist: "Telar",
    src: "https://files.catbox.moe/ur2qo6.mp3",
    img: "/covers/telar.png",
    date: "2025-09-25",
  },

  {
    title: "Casco y Guada en Grey Bar",
    artist: "Casco y Guada",
    src: "https://files.catbox.moe/xyj9u4.mp3",
    img: "/covers/cascoguada.png",
    date: "2025-10-02",
  },

  {
    title: "Jane Doe en Rincón",
    artist: "Jane Doe",
    src: "https://files.catbox.moe/aqajnb.mp3",
    img: "/covers/jane.jpg",
    date: "2025-10-02",
  },

  {
    title: "Armando Alonso en Beertonic",
    artist: "Armando Alonso, Agustín Barbieri, Nicolas Benaghi",
    src: "https://files.catbox.moe/nnubmi.mp3",
    img: "/covers/armand-beer.png",
    date: "2025-10-09",
  },

  {
    title: "Tigran Hamasyan en el Teatro Coliseo",
    artist: "Tigran Hamasyan",
    src: "https://files.catbox.moe/ypys3b.mp3",
    img: "/covers/tigran.jpg",
    date: "2025-10-14",
  },

  {
    title: " Paez de a dos desde el Teatro Trac ",
    artist: "Nico Muchiut y Fede Ratto",
    src: "https://files.catbox.moe/chl3gs.mp3",
    img: "/covers/paez.jpg",
    date: "2025-10-17",
  },

  {
    title: "Inteligencia Accidental en la Ronda de Bandas",
    artist: "Inteligencia Accidental",
    src: "https://files.catbox.moe/edswyr.mp3",
    img: "/covers/ronda2.jpg",
    date: "2025-10-18",
  },

  {
    title: "Base en la Ronda de Bandas",
    artist: "Base",
    src: "https://files.catbox.moe/fc14c0.mp3",
    img: "/covers/ronda2.jpg",
    date: "2025-10-18",
  },

  {
    title: "Sala Roja en la Ronda de Bandas",
    artist: "Sala Roja",
    src: "https://files.catbox.moe/7mai6b.mp3",
    img: "/covers/ronda2.jpg",
    date: "2025-10-18",
  },

  {
    title: "Inteligencia Accidental en el cumple de Lucas",
    artist: "Inteligencia Accidental",
    src: "https://files.catbox.moe/1y3q74.mp3",
    img: "/covers/cumple-lu.jpg",
    date: "2025-10-20",
  },

  {
    title: "Sala Roja en el cumple de Lucas",
    artist: "Sala Roja",
    src: "https://files.catbox.moe/w5yfc2.mp3",
    img: "/covers/cumple-lu.jpg",
    date: "2025-10-20",
  },

  {
    title: "El Ensamble de música contemporánea interpreta a Philip Glass en el Conservatorio Alberto Williams",
    artist: "El Ensamble de música contemporánea",
    src: "https://files.catbox.moe/lg93s3.mp3",
    img: "/covers/glass.jpg",
    date: "2025-10-24",
  },

  {
    title: "Alumnes del Conservatorio Alberto Williams interpretan y Terry Riley a cargo del profesor Pablo Torre ",
    artist: "Alumnes del Conservatorio Alberto Williams",
    src: "https://files.catbox.moe/mwxfv1.mp3",
    img: "/covers/glass.jpg",
    date: "2025-10-24",
  },

  {
    title: "Epifanicas en Garage Avispa",
    artist: "Epifanicas",
    src: "https://files.catbox.moe/2u4twa.mp3",
    img: "/covers/garage.jpg",
    date: "2025-10-24",
  },

  {
    title: "La Ronda Catonga en la Plaza Venezuela",
    artist: "Ronda Catonga",
    src: "https://files.catbox.moe/gy5zk8.mp3",
    img: "/covers/catonga.jpg",
    date: "2025-10-26",
  },

  {
    title: "Fango y Perlas en Beertonic",
    artist: "Fango y Perlas",
    src: "https://files.catbox.moe/e79q6c.mp3",
    img: "/covers/fango.webp",
    date: "2025-10-23",
  },

  {
    title: "Nómada en la Festimaga 2",
    artist: "Nómada",
    src: "https://files.catbox.moe/a7wcqy.mp3",
    img: "/covers/festimaga2.png",
    date: "2025-10-31",
  },

  {
    title: "Sala Roja en la Festimaga 2",
    artist: "Sala Roja",
    src: "https://files.catbox.moe/dyjyrz.mp3",
    img: "/covers/festimaga2.png",
    date: "2025-10-31",
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
    date: "2025-11-06",
  },

  {
    title: "Valkirias en la Plaza Charo Latessa",
    artist: "Valkirias",
    src: "https://files.catbox.moe/nkrss1.mp3",
    img: "/covers/charo.webp",
    date: "2025-11-08",
  },

  {
    title: "Epifanicas en la Fiesta de la Cebada",
    artist: "Epifanicas",
    src: "https://files.catbox.moe/b594ma.mp3",
    img: "/covers/epis-cebada.jpg",
    date: "2025-11-08",
  },

  {
    title: "Maquinaria Divina en el Festival Consciente",
    artist: "Maquinaria Divina",
    src: "https://files.catbox.moe/oh2itu.mp3",
    img: "/covers/festi-cons2.webp",
    date: "2025-11-21",
  },

  {
    title: "Jane Doe en el Festival Consciente",
    artist: "Jane Doe",
    src: "https://files.catbox.moe/o1nk8u.mp3",
    img: "/covers/festi-cons2.webp",
    date: "2025-11-21",
  },

  {
    title: "Base en el Festival Consciente",
    artist: "Base",
    src: "https://files.catbox.moe/q0qqq6.mp3",
    img: "/covers/festi-cons2.webp",
    date: "2025-11-21",
  },

  {
    title: "Sociedad Macabra en el Festival Consciente",
    artist: "Sociedad Macabra",
    src: "https://files.catbox.moe/6um5nk.mp3",
    img: "/covers/festi-cons2.webp",
    date: "2025-11-21",
  },

  {
    title: "Inteligencia Accidental en el Festival Consciente",
    artist: "Inteligencia Accidental",
    src: "https://files.catbox.moe/kpb3y2.mp3",
    img: "/covers/festi-cons2.webp",
    date: "2025-11-21",
  },

  {
    title: "Forrxs en el Festival Consciente",
    artist: "Forrxs",
    src: "https://files.catbox.moe/fw8fd9.mp3",
    img: "/covers/festi-cons2.webp",
    date: "2025-11-21",
  },

  {
    title: "Guada y Abril dúo en el aniversario de Beertonic (extracto).",
    artist: "Guada y Abril",
    src: "https://files.catbox.moe/4jor73.mp3",
    img: "/covers/cumple-beer.jpg",
    date: "2025-11-23",
  },

  {
    title: "Catango Trío en el aniversario de Beertonic",
    artist: "Catango Trío ",
    src: "https://files.catbox.moe/o9yf05.mp3",
    img: "/covers/cumple-beer.jpg",
    date: "2025-11-23",
  },

  {
    title: "Paprika's Band en el aniversario de Beertonic",
    artist: "Paprika's Band",
    src: "https://files.catbox.moe/k000p1.mp3",
    img: "/covers/cumple-beer.jpg",
    date: "2025-11-23",
  },

  {
    title: "Los Pozoz en la Festimaga 3",
    artist: "Los Pozoz",
    src: "https://files.catbox.moe/f0vb1d.mp3",
    img: "/covers/festimaga3.jpg",
    date: "2025-11-28",
  },

  {
    title: "Traumas de la Infancia en la Festimaga 3",
    artist: "Traumas de la Infancia",
    src: "https://files.catbox.moe/s8qfqf.mp3",
    img: "/covers/festimaga3.jpg",
    date: "2025-11-28",
  },

  {
    title: "Reunión de Traumas interpretando Desahogo en la Festimaga 3",
    artist: "Yanqui, Nicanor, Chiquilin Sanchez y Simón (el cantor)",
    src: "https://files.catbox.moe/a08fm2.mp3",
    img: "/covers/festimaga3.jpg",
    date: "2025-11-28",
  },

  {
    title: "Base en el Festival Distorsivo",
    artist: "Base",
    src: "https://files.catbox.moe/8blvc7.mp3",
    img: "/covers/festi-distor.webp",
    date: "2025-11-29",
  },

  {
    title: "Entrance en el Festival Distorsivo",
    artist: "Entrance",
    src: "https://files.catbox.moe/y1rcv1.mp3",
    img: "/covers/festi-distor.webp",
    date: "2025-11-29",
  },

  {
    title: "Muestra fin de ciclo de la NUEVA (escuela de) MÚSICA día 1",
    artist: "Nueva Escuela de Música",
    src: "https://files.catbox.moe/sg11i3.mp3",
    img: "/covers/nueva.jpg",
    date: "2025-12-03",
  },

  {
    title: "Muestra fin de ciclo de la NUEVA (escuela de) MÚSICA día 2",
    artist: "Nueva Escuela de Música",
    src: "https://files.catbox.moe/llvbhj.mp3",
    img: "/covers/nueva.jpg",
    date: "2025-12-03",
  },

  {
    title: "Los Pozoz en el Mad Monky Fest",
    artist: "Los Pozoz",
    src: "https://files.catbox.moe/3g4um0.mp3",
    img: "/covers/mad.webp",
    date: "2025-12-06",
  },

  {
    title: "Nómada en el Mad Monky Fest",
    artist: "Nómada",
    src: "https://files.catbox.moe/dcp23i.mp3",
    img: "/covers/mad.webp",
    date: "2025-12-06",
  },

  {
    title: "Sociedad Macabra en el Mad Monky Fest",
    artist: "Sociedad Macabra",
    src: "https://files.catbox.moe/slx3uw.mp3",
    img: "/covers/mad.webp",
    date: "2025-12-06",
  },

  {
    title: "Parasomnia en el Mad Monky Fest",
    artist: "Parasomnia",
    src: "https://files.catbox.moe/1l50w5.mp3",
    img: "/covers/mad.webp",
    date: "2025-12-06",
  },

  {
    title: "Epifanicas Bloque 1 en Sala Biaus",
    artist: "Epifanicas",
    src: "https://files.catbox.moe/51g1x3.mp3",
    img: "/covers/epi-biaus.jpg",
    date: "2025-12-13",
  },

  {
    title: "Hernán de Bragado en Sala Biaus",
    artist: "Hernán de Bragado",
    src: "https://files.catbox.moe/dcs0qf.mp3",
    img: "/covers/epi-biaus.jpg",
    date: "2025-12-13",
  },

  {
    title: "Epifanicas Bloque 2 en Sala Biaus",
    artist: "Epifanicas",
    src: "https://files.catbox.moe/mqcg8y.mp3",
    img: "/covers/epi-biaus.jpg",
    date: "2025-12-13",
  },

  {
    title: "Drama en Sala Biaus",
    artist: "Drama",
    src: "https://files.catbox.moe/u87zop.mp3",
    img: "/covers/bad-drama.jpg",
    date: "2025-12-27",
  },

  {
    title: "Los Bad Seed en Sala Biaus",
    artist: "Los Bad Seed",
    src: "https://files.catbox.moe/1q21vg.mp3",
    img: "/covers/bad-drama.jpg",
    date: "2025-12-27",
  },

  {
    title: "Sociedad Macabra en año nuevo fest",
    artist: "Sociedad Macabra",
    src: "https://files.catbox.moe/nz514m.mp3",
    img: "/covers/año.png",
    date: "2025-12-31",
  },

  {
    title: "Parasomnia en año nuevo fest",
    artist: "Parasomnia",
    src: "https://files.catbox.moe/a6e37m.mp3",
    img: "/covers/año.png",
    date: "2025-12-31",
  },

  {
    title: "IA en año nuevo fest",
    artist: "Inteligencia Accidental",
    src: "https://files.catbox.moe/i60k6t.mp3",
    img: "/covers/año.png",
    date: "2025-12-31",
  },

  {
    title: "Los Bad Seed en año nuevo fest",
    artist: "Los Bad Seed",
    src: "https://files.catbox.moe/hgf90e.mp3",
    img: "/covers/año.png",
    date: "2025-12-31",
  },


  {
    title: "Epifanicas en Encuentro por las Artes",
    artist: "Epifanicas",
    src: "https://files.catbox.moe/3rjs9s.mp3",
    img: "/covers/epi-roco-sun.jpg",
    date: "2026-01-09",
  },


  {
    title: "Sunglasses en Encuentro por las Artes",
    artist: "Sunglasses",
    src: "https://files.catbox.moe/ooo8y2.mp3",
    img: "/covers/epi-roco-sun.jpg",
    date: "2026-01-09",
  },


  {
    title: "Roco y los Chacks en Encuentro por las Artes",
    artist: "Roco y los Chacks",
    src: "https://files.catbox.moe/xkdrvl.mp3",
    img: "/covers/epi-roco-sun.jpg",
    date: "2026-01-09",
  },

  {
    title: "Cínica en Sala Biaus",
    artist: "Cínica",
    src: "https://files.catbox.moe/uhjd18.mp3",
    img: "/covers/biaus-cin-ia-mr-nomad.jpg",
    date: "2026-01-16",
  },

  {
    title: "Inteligencia Accidental en Sala Biaus 16-01-26",
    artist: "Inteligencia Accidental",
    src: "https://files.catbox.moe/gulf4e.mp3",
    img: "/covers/biaus-cin-ia-mr-nomad.jpg",
    date: "2026-01-16",
  },

  {
    title: "Sr Wilson en Sala Biaus",
    artist: "Sr Wilson",
    src: "https://files.catbox.moe/8t1ot8.mp3",
    img: "/covers/biaus-cin-ia-mr-nomad.jpg",
    date: "2026-01-16",
  },

  {
    title: "Nómada en Sala Biaus",
    artist: "Nómada",
    src: "https://files.catbox.moe/uvw3ce.mp3",
    img: "/covers/biaus-cin-ia-mr-nomad.jpg",
    date: "2026-01-16",
  },

  {
    title: "Homenaje a El Kuelgue",
    artist: "Kuelguero's band",
    src: "https://files.catbox.moe/9j5gxa.mp3",
    img: "/recitales/ruta30/kuelgue/featured.png",
    date: "2026-01-22",
  },

  {
    title: "Oesterheld en Sala Biaus",
    artist: "Oesterheld",
    src: "https://files.catbox.moe/4wzf3v.mp3",
    img: "/recitales/sala-biaus/oesterheld/featured.jpg",
    date: "2026-01-24",
  },

  {
    title: "Nómada en Galpón Beer",
    artist: "Nómada",
    src: "/audio/galpon/nomada.mp3",
    img: "/covers/nomad-cala-down.jpg",
    date: "2026-01-30",
  },

  {
    title: "San Calavera en Galpón Beer",
    artist: "San Calavera",
    src: "/audio/galpon/calavera.mp3",
    img: "/covers/nomad-cala-down.jpg",
    date: "2026-01-30",
  },

  {
    title: "Downfall en Galpón Beer",
    artist: "Downfall",
    src: "/audio/galpon/downfall.mp3",
    img: "/covers/nomad-cala-down.jpg",
    date: "2026-01-30",
  },

  {
    title: "Epifanicas en Lap Cantina",
    artist: "Epifanicas",
    src: "https://files.catbox.moe/bow1th.mp3",
    img: "/recitales/lap-cantina/epifanicas/featured.jpg",
    date: "2026-02-06",
  },


  {
    title: "Oesterheld en Ruta 30",
    artist: "Oesterheld",
    src: "https://files.catbox.moe/qhrn7g.mp3",
    img: "/recitales/ruta30/oesterheld/featured.jpg",
    date: "2026-02-06",
  },

  {
    title: "Entrance en Sala Biaus",
    artist: "Entrance",
    src: "https://files.catbox.moe/iafe6j.mp3",
    img: "/covers/entrance-ia-sabo-biaus.png",
    date: "2026-02-07",
  },

  {
    title: "Inteligencia Accidental en Sala Biaus",
    artist: "Inteligencia Accidental",
    src: "https://files.catbox.moe/36tdec.mp3",
    img: "/covers/entrance-ia-sabo-biaus.png",
    date: "2026-02-07",
  },

  {
    title: "Sabotaje en Sala Biaus",
    artist: "Sabotaje",
    src: "https://files.catbox.moe/bvkj6x.mp3",
    img: "/covers/entrance-ia-sabo-biaus.png",
    date: "2026-02-07",
  },

  {
    title: "Cinica en Encuentro por las Artes",
    artist: "Cinica",
    src: "https://files.catbox.moe/mcigps.mp3",
    img: "/covers/anticover13.png",
    date: "2026-02-13",
  },

  {
    title: "Facu Dovidio en Encuentro por las Artes",
    artist: "Facu Dovidio",
    src: "https://files.catbox.moe/n29flz.mp3",
    img: "/covers/anticover13.png",
    date: "2026-02-13",
  },

  {
    title: "Paprika's Band en Encuentro por las Artes",
    artist: "Paprika's Band",
    src: "https://files.catbox.moe/6jr85k.mp3",
    img: "/covers/anticover13.png",
    date: "2026-02-13",
  },

  {
    title: "SOFA en Beertonic",
    artist: "SOFA",
    src: "https://files.catbox.moe/rqmo87.mp3",
    img: "/covers/sofa.png",
    date: "2026-02-15",
  },

  {
    title: "Fronda y Raíz en la Varela",
    artist: "Fronda y Raíz",
    src: "https://files.catbox.moe/haq3r8.mp3",
    img: "/covers/raiz.jpg",
    date: "2026-02-20",
  },

  {
    title: "Juanito Alimaña en Encuentro por las Artes",
    artist: "Juanito Alimaña",
    src: "https://files.catbox.moe/pmd0a9.mp3",
    img: "/covers/juanito.jpg",
    date: "2026-02-27",
  },

  {
    title: "Paprika's Band en Encuentro por las Artes",
    artist: "Paprika's Band",
    src: "https://files.catbox.moe/npl2es.mp3",
    img: "/covers/juanito.jpg",
    date: "2026-02-27",
  },

  {
    title: "Muchiut y los monjes del dudaismo en Encuentro por las Artes",
    artist: "Muchiut y los monjes del dudaismo",
    src: "https://files.catbox.moe/txexq5.mp3",
    img: "/covers/juanito.jpg",
    date: "2026-02-27",
  },

  {
    title: "Rey Midas en Club Conjura",
    artist: "Rey Midas",
    src: "/audio/conjura/Rey-Midas-28-2-26.mp3",
    img: "/covers/seed-capi.jpg",
    date: "2026-02-28",
  },

  {
    title: "Ayende en Club Conjura",
    artist: "Ayende",
    src: "/audio/conjura/Ayende-28-2-26.mp3",
    img: "/covers/seed-capi.jpg",
    date: "2026-02-28",
  },

  {
    title: "VIK en Club Conjura",
    artist: "VIK",
    src: "/audio/conjura/VIK-28-2-26.mp3",
    img: "/covers/seed-capi.jpg",
    date: "2026-02-28",
  },

  {
    title: "Velvet en Club Conjura",
    artist: "Velvet",
    src: "/audio/conjura/Velvet-28-2-26.mp3",
    img: "/covers/seed-capi.jpg",
    date: "2026-02-28",
  },

  {
    title: "Nancy desde el Tren Sarmiento",
    artist: "Nancy",
    src: "https://files.catbox.moe/kswukp.mp3",
    img: "/recitales/tren/nancy/featured.png",
    date: "2026-02-29",
  },


  {
    title: "Armando Alonso Trío en Sala Belgrano",
    artist: "Armando Alonso",
    src: "https://files.catbox.moe/didtx2.mp3",
    img: "/recitales/sala-belgrano/armando/featured.jpg",
    date: "2026-03-06",
  },


  {
    title: "Base en Sala Biaus",
    artist: "Base",
    src: "https://files.catbox.moe/1jjkyb.mp3",
    img: "/covers/corpo.jpg",
    date: "2026-03-06",
  },

  {
    title: "Ismael es de verdad en Sala Biaus",
    artist: "Ismael es de verdad",
    src: "https://files.catbox.moe/y5fhfz.mp3",
    img: "/covers/corpo.jpg",
    date: "2026-03-06",
  },

  {
    title: "Corpo Porco en Sala Biaus",
    artist: "Corpo Porco",
    src: "https://files.catbox.moe/ts1yj4.mp3",
    img: "/covers/corpo.jpg",
    date: "2026-03-06",
  },

  {
    title: "Sabotage en El Portal del Tango",
    artist: "Sabotage",
    src: "https://files.catbox.moe/59gial.mp3",
    img: "/recitales/el-portal-del-tango/sabotage/featured.jpg",
    date: "2026-03-13",

  },

  {
    title: "Armando Alonso en Beertonic 20-3-26",
    artist: "Armando Alonso",
    src: "https://files.catbox.moe/arm4rw.mp3",
    img: "/recitales/beertonic/armand2/featured.png",
    date: "2026-03-26",

  },

  {
    title: "La Reja Estudio acústico en Sala Biaus",
    artist: "La Reja Estudio",
    src: "https://files.catbox.moe/6zk2lj.mp3",
    img: "/covers/cinidrama.png",
    date: "2026-03-21",

  },

  {
    title: "Cínica en Sala Biaus",
    artist: "Cínica",
    src: "https://files.catbox.moe/ebajw2.mp3",
    img: "/covers/cinidrama.png",
    date: "2026-03-21",

  },

  {
    title: "DRAMA en Sala Biaus",
    artist: "DRAMA",
    src: "https://files.catbox.moe/4xqu71.mp3",
    img: "/covers/cinidrama.png",
    date: "2026-03-21",

  },

  {
    title: "Epifanicas en Sala Belgrano",
    artist: "Epifanicas",
    src: "https://files.catbox.moe/4h9707.mp3",
    img: "/recitales/sala-belgrano/epi-blues/featured.png",
    date: "2026-03-27",

  },

  {
    title: "Pueblues en Sala Belgrano",
    artist: "Pueblues",
    src: "https://files.catbox.moe/78zr8t.mp3",
    img: "/recitales/sala-belgrano/epi-blues/featured.png",
    date: "2026-03-27",

  },

  {
    title: "Eruca Sativa en el Club Racing",
    artist: "Eruca Sativa",
    src: "https://files.catbox.moe/f9iilj.mp3",
    img: "/recitales/club-racing/eruca/featured.webp",
    date: "2026-05-08",

  },

  {
    title: "Dudosa Procedencia en el Club Juventus",
    artist: "Dudosa Procedencia",
    src: "https://files.catbox.moe/aqbbib.mp3",
    img: "/recitales/juventus/dudosa-inteligencia-corpo/featured.webp",
    date: "2026-05-09",

  },

  {
    title: "Intelogencia Accidental en el Club Juventus",
    artist: "Intelogencia Accidental",
    src: "https://files.catbox.moe/cxp9ne.mp3",
    img: "/recitales/juventus/dudosa-inteligencia-corpo/featured.webp",
    date: "2026-05-09",

  },

  {
    title: "Corpo Porco en el Club Juventus",
    artist: "Corpo Porco",
    src: "https://files.catbox.moe/aeakx3.mp3",
    img: "/recitales/juventus/dudosa-inteligencia-corpo/featured.webp",
    date: "2026-05-09",

  },

  {
    title: "Maquinaria Divina Ronda de Bandas 3",
    artist: "Maquinaria Divina",
    src: "https://files.catbox.moe/2ph46d.mp3",
    img: "/recitales/la-ronda/rondadebandas-3/featured.jpg",
    date: "2026-07-10",

  },

  {
    title: "Catango Trio Ronda de Bandas 3",
    artist: "Catango Trio",
    src: "https://files.catbox.moe/3zcs4e.mp3",
    img: "/recitales/la-ronda/rondadebandas-3/featured.jpg",
    date: "2026-07-10",

  },


  {
    title: "Cínica Ronda de Bandas 3",
    artist: "Cínica",
    src: "https://files.catbox.moe/g0xnhf.mp3",
    img: "/recitales/la-ronda/rondadebandas-3/featured.jpg",
    date: "2026-07-10",

  },

  {
    title: "Paprika's Band en Ruta 30",
    artist: "Paprika's Band",
    src: "https://files.catbox.moe/g0xnhf.mp3",
    img: "/recitales/ruta30/paprikas/featured.jpg",
    date: "2026-07-17",

  },

  {
    title: "Entrance en Sala Biaus",
    artist: "Entrance",
    src: "https://audiogusano.neocities.org/audio/sala-biaus/entrancinibase-17-7-26/entrance-sala-11-7-26.mp3",
    img: "/recitales/sala-biaus/entrance-cinica-base/featured.webp",
    date: "2026-07-18",

  },

  {
    title: "Cínica en Sala Biaus",
    artist: "Cínica",
    src: "https://audiogusano.neocities.org/audio/sala-biaus/entrancinibase-17-7-26/cinica-sala7-26.mp3",
    img: "/recitales/sala-biaus/entrance-cinica-base/featured.webp",
    date: "2026-07-18",

  },

  {
    title: "Base en Sala Biaus",
    artist: "Base",
    src: "https://audiogusano.neocities.org/audio/sala-biaus/entrancinibase-17-7-26/base-biaus-7-26.mp3",
    img: "/recitales/sala-biaus/entrance-cinica-base/featured.webp",
    date: "2026-07-18",

  },



];

songs.reverse();

// Map songs to dates using Hugo's recitalData or title parsing
songs.forEach(song => {
  if (song.date) return;

  // 1. Try to match by audio src URL
  const srcMatch = window.recitalData.find(r => r.audios && r.audios.includes(song.src));
  if (srcMatch) {
    song.date = srcMatch.date;
    return;
  }
  
  // 2. Fallback: Try to match by img path
  if (song.img && song.img.includes('/recitales/')) {
    const cleanImgPath = song.img.replace(/\/[^\/]+$/, '');
    const match = window.recitalData.find(r => {
      const cleanPermalink = r.permalink.replace(/\/$/, '');
      return cleanImgPath.includes(cleanPermalink) || cleanPermalink.includes(cleanImgPath);
    });
    if (match) {
      song.date = match.date;
      return;
    }
  }
  
  // 3. Fallback: try to match by title (e.g. DD-MM-YY or DD-MM-YYYY)
  if (song.title) {
    const dateMatch = song.title.match(/(\d{1,2})-(\d{1,2})-(\d{2,4})/);
    if (dateMatch) {
      const day = dateMatch[1].padStart(2, '0');
      const month = dateMatch[2].padStart(2, '0');
      let year = dateMatch[3];
      if (year.length === 2) year = '20' + year;
      song.date = `${year}-${month}-${day}`;
    }
  }
});

const audio = new Audio();
audio.preload = "none";

// Extract unique bands from all song artists to populate band select dropdown
const searchFilter = document.getElementById("searchFilter");
const bandFilter = document.getElementById("bandFilter");
const dateFilter = document.getElementById("dateFilter");
const clearDateBtn = document.getElementById("clearDateBtn");
const toggleFiltersBtn = document.getElementById("toggleFiltersBtn");
const playlistFilters = document.querySelector(".playlist-filters");

// Toggle filters visibility
toggleFiltersBtn.addEventListener('click', () => {
  playlistFilters.classList.toggle("hidden");
  toggleFiltersBtn.classList.toggle("active");
});

const uniqueDates = new Set();
songs.forEach(song => {
  if (song.date) {
    uniqueDates.add(song.date);
  }
});

const bands = new Set();
songs.forEach(song => {
  if (song.artist) {
    // Split by comma in case there are multiple bands/artists listed
    song.artist.split(',').forEach(artistName => {
      const clean = artistName.trim();
      if (clean && clean !== "Unknown Artist") {
        bands.add(clean);
      }
    });
  }
});

// Sort and populate band filter select
const sortedBands = Array.from(bands).sort((a, b) => a.localeCompare(b, undefined, { sensitivity: 'base' }));
sortedBands.forEach(band => {
  const opt = document.createElement("option");
  opt.value = band;
  opt.textContent = band;
  bandFilter.appendChild(opt);
});

// Filter states
let filteredSongs = [...songs];

function normalizeText(str) {
  return str.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
}

function filterSongs() {
  const searchQuery = normalizeText(searchFilter.value.trim());
  const selectedBand = bandFilter.value.toLowerCase();
  const selectedDate = dateFilter.value;
  
  filteredSongs = songs.filter(song => {
    let searchMatch = true;
    if (searchQuery) {
      const titleMatch = song.title && normalizeText(song.title).includes(searchQuery);
      const artistMatch = song.artist && normalizeText(song.artist).includes(searchQuery);
      searchMatch = titleMatch || artistMatch;
    }

    // Band filter
    let bandMatch = true;
    if (selectedBand) {
      bandMatch = song.artist && song.artist.toLowerCase().includes(selectedBand);
    }
    
    // Date filter
    let dateMatch = true;
    if (selectedDate) {
      dateMatch = song.date === selectedDate;
    }
    
    return searchMatch && bandMatch && dateMatch;
  });
  
  populateSongList();
  
  if (viewMode === "grid") {
    populateCoverGrid();
  }
  
  // If shuffle is active, update shuffle queue to respect filter
  if (isShuffled) {
    updateShuffleQueue();
  }
}

function populateSongList() {
  songListEl.innerHTML = "";
  filteredSongs.forEach((song) => {
    const originalIndex = songs.indexOf(song);
    const li = document.createElement("li");
    li.dataset.index = originalIndex;
    
    if (originalIndex === currentSongIndex) {
      li.classList.add("active");
    }
    
    let dateBadge = "";
    if (song.date) {
      const parts = song.date.split('-');
      if (parts.length === 3) {
        dateBadge = `<span class="song-date">${parts[2]}/${parts[1]}</span>`;
      }
    }

    li.innerHTML = `
      <div class="song-info-meta">
        <span class="song-title-text">${song.title || "Unknown"}</span>
        <span class="song-artist-text">${song.artist || "Unknown Artist"}</span>
      </div>
      <div class="song-duration-meta">
        ${dateBadge}
        <span class="song-duration"></span>
      </div>
    `;
    songListEl.appendChild(li);
  });
}

function populateCoverGrid() {
  coverGrid.innerHTML = "";
  filteredSongs.forEach((song) => {
    const originalIndex = songs.indexOf(song);
    const item = document.createElement("div");
    item.className = "cover-grid-item";
    item.dataset.index = originalIndex;
    if (originalIndex === currentSongIndex) {
      item.classList.add("active");
    }
    const img = document.createElement("img");
    img.src = song.img || "/covers/default.jpg";
    img.alt = song.title || "Cover";
    img.loading = "lazy";
    img.onerror = function () {
      this.onerror = null;
      this.src = 'https://placehold.co/200x200/333333/FFFFFF?text=No+Art';
    };
    item.appendChild(img);
    const titleEl = document.createElement("span");
    titleEl.className = "cover-title";
    titleEl.textContent = song.title || "";
    item.appendChild(titleEl);
    item.addEventListener("click", () => {
      currentSongIndex = originalIndex;
      isPlaying = true;
      loadSong(currentSongIndex);
      audio.play();
      closeDrawer();
    });
    coverGrid.appendChild(item);
  });
}

function loadSong(index) {
  const song = songs[index];
  title.textContent = song.title || "Unknown Title";
  artist.textContent = song.artist || "Unknown Artist";

  albumArt.src = song.img || 'images/default.jpg';
  albumArt.onerror = function () {
    this.onerror = null;
    this.src = 'https://placehold.co/250x250/333333/FFFFFF?text=No+Art';
  };

  audio.src = song.src;

  // Update active song in playlist
  songListEl.querySelectorAll("li").forEach((item) => {
    const itemIndex = parseInt(item.dataset.index);
    item.classList.toggle("active", itemIndex === index);
  });
  coverGrid.querySelectorAll(".cover-grid-item").forEach((item) => {
    const itemIndex = parseInt(item.dataset.index);
    item.classList.toggle("active", itemIndex === index);
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

// Bind filters input events
searchFilter.addEventListener('input', filterSongs);
bandFilter.addEventListener('change', filterSongs);
dateFilter.addEventListener('change', filterSongs);
clearDateBtn.addEventListener('click', () => {
  dateFilter.value = "";
  datePickerLabel.textContent = "Seleccionar fecha";
  document.querySelectorAll(".cal-day-selected").forEach(el => el.classList.remove("cal-day-selected"));
  filterSongs();
});

// Custom date picker calendar
const datePickerBtn = document.getElementById("datePickerBtn");
const datePickerDropdown = document.getElementById("datePickerDropdown");
const datePickerLabel = document.getElementById("datePickerLabel");
const calGrid = document.getElementById("calGrid");
const calTitle = document.getElementById("calTitle");
const prevMonth = document.getElementById("prevMonth");
const nextMonth = document.getElementById("nextMonth");

let calMonth = new Date().getMonth();
let calYear = new Date().getFullYear();

function renderCalendar(month, year) {
  const monthNames = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"];
  calTitle.textContent = `${monthNames[month]} ${year}`;

  const firstDay = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const startOffset = firstDay === 0 ? 6 : firstDay - 1;

  calGrid.innerHTML = "";

  for (let i = 0; i < startOffset; i++) {
    const el = document.createElement("div");
    el.classList.add("cal-empty");
    calGrid.appendChild(el);
  }

  for (let d = 1; d <= daysInMonth; d++) {
    const el = document.createElement("div");
    el.textContent = d;
    el.classList.add("cal-day");

    const dateStr = `${year}-${String(month + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;

    if (uniqueDates.has(dateStr)) {
      el.classList.add("cal-day-has-event");
    }

    const today = new Date();
    if (d === today.getDate() && month === today.getMonth() && year === today.getFullYear()) {
      el.classList.add("cal-day-today");
    }

    if (dateFilter.value === dateStr) {
      el.classList.add("cal-day-selected");
    }

    el.addEventListener("click", () => {
      document.querySelectorAll(".cal-day-selected").forEach(el => el.classList.remove("cal-day-selected"));
      el.classList.add("cal-day-selected");
      dateFilter.value = dateStr;
      const parts = dateStr.split("-");
      datePickerLabel.textContent = `${parts[2]}/${parts[1]}/${parts[0]}`;
      datePickerDropdown.classList.remove("show");
      filterSongs();
    });

    calGrid.appendChild(el);
  }
}

prevMonth.addEventListener("click", () => {
  calMonth--;
  if (calMonth < 0) { calMonth = 11; calYear--; }
  renderCalendar(calMonth, calYear);
});

nextMonth.addEventListener("click", () => {
  calMonth++;
  if (calMonth > 11) { calMonth = 0; calYear++; }
  renderCalendar(calMonth, calYear);
});

datePickerBtn.addEventListener("click", (e) => {
  e.stopPropagation();
  datePickerDropdown.classList.toggle("show");
  if (datePickerDropdown.classList.contains("show")) {
    renderCalendar(calMonth, calYear);
  }
});

document.addEventListener("click", (e) => {
  if (!datePickerDropdown.contains(e.target) && e.target !== datePickerBtn) {
    datePickerDropdown.classList.remove("show");
  }
});

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
    let idx = filteredSongs.indexOf(songs[currentSongIndex]);
    if (idx === -1) {
      currentSongIndex = songs.indexOf(filteredSongs[filteredSongs.length - 1]);
    } else {
      idx = (idx - 1 + filteredSongs.length) % filteredSongs.length;
      currentSongIndex = songs.indexOf(filteredSongs[idx]);
    }
  }
  isPlaying = true;
  loadSong(currentSongIndex);
  audio.play();
};

nextBtn.onclick = () => {
  if (isShuffled && shuffledSongs.length > 0) {
    let currentShuffledIndex = shuffledSongs.indexOf(currentSongIndex);
    currentShuffledIndex = (currentShuffledIndex + 1) % shuffledSongs.length;
    currentSongIndex = shuffledSongs[currentShuffledIndex];
  } else {
    let idx = filteredSongs.indexOf(songs[currentSongIndex]);
    if (idx === -1) {
      currentSongIndex = songs.indexOf(filteredSongs[0]);
    } else {
      idx = (idx + 1) % filteredSongs.length;
      currentSongIndex = songs.indexOf(filteredSongs[idx]);
    }
  }
  isPlaying = true;
  loadSong(currentSongIndex);
  audio.play();
};

songListEl.onclick = (e) => {
  let targetLi = e.target.closest("li");
  if (targetLi && targetLi.dataset.index !== undefined) {
    currentSongIndex = parseInt(targetLi.dataset.index);
    isPlaying = true;
    loadSong(currentSongIndex);
    audio.play();

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
  const durationStr = formatTime(audio.duration);
  durationEl.textContent = durationStr;

  const activeLi = songListEl.querySelector(`li[data-index="${currentSongIndex}"]`);
  if (activeLi) {
    const durationSpan = activeLi.querySelector('.song-duration');
    if (durationSpan) {
      durationSpan.textContent = durationStr;
    }
  }
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
    let idx = filteredSongs.indexOf(songs[currentSongIndex]);
    if (idx === filteredSongs.length - 1 && !isShuffled) {
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
  repeatBtn.style.color = repeatMode === "none" ? "#fff" : "var(--player-primary)";
};

function updateShuffleQueue() {
  if (isShuffled) {
    const filteredIndices = filteredSongs.map(s => songs.indexOf(s));
    shuffledSongs = shuffleArray(filteredIndices);
    const idx = shuffledSongs.indexOf(currentSongIndex);
    if (idx > -1) shuffledSongs.splice(idx, 1);
    shuffledSongs.unshift(currentSongIndex);
  } else {
    shuffledSongs = [];
  }
}

shuffleBtn.onclick = () => {
  isShuffled = !isShuffled;
  shuffleBtn.style.color = isShuffled ? "var(--player-primary)" : "#fff";
  updateShuffleQueue();
};

viewToggle.onclick = () => {
  if (viewMode === "list") {
    viewMode = "grid";
    viewToggle.textContent = "list";
    viewToggle.classList.add("active");
    songListEl.classList.add("hidden");
    coverGrid.classList.add("active");
    populateCoverGrid();
  } else {
    viewMode = "list";
    viewToggle.textContent = "grid_view";
    viewToggle.classList.remove("active");
    songListEl.classList.remove("hidden");
    coverGrid.classList.remove("active");
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

// Close logic for the "X" button and the background overlay
closePlaylist.onclick = closeDrawer;
overlay.onclick = closeDrawer;
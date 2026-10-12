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
// Song data is injected by Hugo from data/shows.yml (see layouts/music.html).
// window.shows is already sorted newest first, so no reverse() is needed.
const songs = window.shows || [];

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
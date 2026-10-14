<!--
RECITAL NUEVO - el audio ya no va con {{< audio src="" >}}: vive en
data/shows.yml y lo dibuja el shortcode `track`, que ademas agrega solo el
link de descarga en WAV/FLAC. El link a Internet Archive se escribe a mano.

Pasos:
  1. La pagina va en content/recitales/<espacio>/<show>/index.md
     (el id del show en el catalogo es esa misma ruta, sin el index.md).
  2. Antes de la pagina, agregar el show a data/shows.yml: id, date, title,
     tracks[] (con id, artist y title; los archivos los completa el script),
     space, bands, cover y page.
  3. Completar los archivos y la duracion desde archive.org:
         python3 scripts/sync-archive.py --show <espacio>/<show> --write
     Si el item no resuelve solo, esta la lista OVERRIDES del script.
  4. Un {{< track >}} por pista, con el id de la pista del catalogo.
  5. cover: la imagen del bundle, p.ej. /recitales/<espacio>/<show>/featured.jpg
  6. weight: el negativo siguiente al mas bajo que haya (lo mas nuevo primero).
-->
---
date : 2026-
title : ""
weight: -
bandas: []
espacios: []
author: "Gusanoide"
draft: false
showHero: true
heroStyle: background
---

# ![banda](featured.jpg)

# [Banda](https://www.instagram.com/banda/) en [Espacio](https://www.instagram.com/espacio/)

---

{{< track show="espacio/show" track="banda" >}}

[Artículo en Internet Archive](https://archive.org/details/ITEM)
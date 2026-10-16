---
title: "Flyers"
showDate: false
weight: -3
bandas: []
espacios: []
author: "Gusanoide"
draft: false
showHero: true
heroStyle: background
# The theme normally reserves 200px above the content so it clears the fixed
# hero backdrop. The carousel wants that space for the cover, so it is off
# here; the h1 sits directly under the nav instead.
layoutBackgroundHeaderSpace: false
layoutBackgroundBlu: true
---

<!-- The gallery itself lives in layouts/flyers/single.html, which overrides
     the theme's single.html for this section. It is built from the recital
     pages under content/recitales, plus whatever sits in static/covers, so
     adding a show is the only step needed to get a flyer into the archive.

     This is separate from layouts/shortcodes/gallery.html, which the homepage
     uses for upcoming events and which reads data/flyers.yml. -->

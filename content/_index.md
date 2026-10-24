---
title: Anuncio
---

{{< new title="Subí tu música." image="/images/material.gif" >}}

Si tenes algo grabado que quieras compartir con la comunidad, ahora podes auto-publicarte usando el botón "Subí tu material" y en pocos minutos aparecerá en Nuevos Lanzamientos.

{{< /new >}}


{{< webamp >}}

# Próximos eventos

{{< gallery "flyers" >}}

<br>

<!-- The Cloudflare Worker from worker-flyers.js. It commits the upload into
     Sorete33/audiogusano-flyers and dispatches this repo's deploy workflow.
     An HTML comment, not a Hugo {{/* */}} one: this is a content file, not a
     template, so Go template comments render verbatim instead of being
     stripped. -->
<center>{{< flyer-upload url="https://audiogusano-flyers.falopa33.workers.dev" >}}</center>

<br>

# Nuevos Lanzamientos

{{< gallery-ext "lanzamientos" >}}

<br>

<center>{{< lanzamientos-upload url="https://audiogusano-flyers.falopa33.workers.dev" >}}</center>

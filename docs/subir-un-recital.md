# Subir un recital nuevo

Cómo pasar de "tengo los masters en una carpeta" a "el recital está en
archive.org y con su entrada en el sitio", sin pasos manuales que se pierdan.

Todo lo hace `scripts/upload-recital.py`. El archivo `recital.txt` que va al
lado de los masters es lo que mantiene cada carpeta identificada: una carpeta
por recital, y cada una dice de qué recital es.

## Lo que hace el script

1. Lee el `recital.txt` y valida los datos.
2. Resuelve qué archivo es de qué banda y arma el nombre canónico de cada
   pista: `NN - <Banda> - <Evento> (<fecha>).wav`.
   **Los masters no se tocan**: se copian a un directorio temporal con ese
   nombre y se sube desde ahí.
3. Sube el item a archive.org con la CLI `ia`, con la metadata que usa el
   catálogo.
4. Espera a que archive.org derive el `.mp3` (y el `.flac`) de cada original.
   archive.org deriva en background: sin esto, el catálogo no encuentra
   archivo que reproducir.
5. Inserta el esqueleto del show en `data/shows.yml`.
6. Corre `scripts/sync-archive.py`, que es el que llena los tracks
   (`mp3`/`flac`/`wav` + duraciones) leyendo la metadata del item.
7. Crea `content/recitales/<venue>/<show>/index.md` con un `{{< track >}}` por
   pista, y copia el flyer como `featured.<ext>`.

El paso 6 es el importante: **`sync-archive.py` sigue siendo la única fuente
de verdad de los tracks**. El script de subida no reimplementa el matcher, lo
llama. Si un show no matchea, el fix es un `OVERRIDES` en
`scripts/sync-archive.py`, igual que siempre.

## Uso

```bash
# 1. Copiar el script a la carpeta de los masters
cp ~/web/gusano-master/scripts/upload-recital.py /ruta/a/los/masters/

# 2. Escribir el recital.txt (o usar --init para que lo genere)
cd /ruta/a/los/masters
python3 upload-recital.py --init

# 3. Ver qué haría, sin tocar nada
python3 upload-recital.py --dry-run

# 4. Ejecutarlo
python3 upload-recital.py
```

Si los masters están fuera del repo, el script lo busca por su cuenta en
`~/web/gusano-master`. Si el repo estuviera en otro lado:

```bash
python3 upload-recital.py --repo /ruta/al/repo
# o
export GUSANO_REPO=/ruta/al/repo
```

## El archivo `recital.txt`

Es YAML. Lo que está comentado es opcional.

```yaml
# Nombre del evento. Va en el título del item y en el nombre de los archivos.
title: Festimaga 6

# Espacio (la sala). Va en el item y en el catálogo.
venue: La Maga

# Fecha real del show. IMPORTANTE: tiene que ser la misma que la del item en
# archive.org, porque es lo que usa el matcher para cruzarlos.
date: 2026-11-14

# Slug de la página: content/recitales/<venue-slug>/<slug>/
slug: festimaga6

# Bandas que tocaron (van a data/shows.yml y al filtro de /flyers/).
bands:
  - Mate Jazz
  - Black Mamba

# Una pista por archivo. "file" es el nombre del master, "band" la banda.
# Si no lo ponés, el script intenta adivinar por el nombre del archivo.
tracks:
  - file: 01 - mate jazz.wav
    band: Mate Jazz
  - file: 02 - black mamba.wav
    band: Black Mamba

# Flyer opcional: se copia a la página como featured.<ext> y la página entra
# sola al archivo de /flyers/.
featured: flyer.jpg

# Metadata extra del item de archive.org (opcional).
metadata:
  # creator: gusanoide
  # coverage: Chivilcoy, Buenos Aires, Argentina
```

Si se omiten `tracks:`, el script toma todos los audios de la carpeta y
adivina la banda por el nombre del archivo. Si no puede, avisa y hay que
agregar la pista al archivo.

`slug` importa: con `venue: La Maga` y `slug: festimaga6` la página queda en
`content/recitales/la-maga/festimaga6/`, y ese path es el `id` del show en
`data/shows.yml`.

## Qué metadata se sube

La misma que usan los items que ya están:

| campo | valor |
|---|---|
| `title` | `<Evento> en <Venue> (AAAA-MM-DD)` |
| `creator` | `gusanoide` |
| `date` | la fecha del show |
| `venue` | el espacio |
| `coverage` | `Chivilcoy, Buenos Aires, Argentina` |
| `description` | `Grabación en vivo de <Evento> en <Venue> el día <fecha>.` |
| `mediatype` | `audio` |
| `collection` | `opensource_audio` |
| identifier | `live-<fecha>-<slug>` |

El `date` del item tiene que ser **la fecha real del show**: es lo primero que
mira el matcher para cruzar un show con su item. Si no coincide, el show
queda sin resolver y hay que agregar un `OVERRIDES` en `sync-archive.py`.

## Otros flags

| flag | para qué |
|---|---|
| `--dry-run` | planifica y muestra todo, no sube ni escribe nada |
| `--init` | escribe un `recital.txt` de ejemplo en la carpeta |
| `--skip-upload` | el item ya está subido: arma la entrada del catálogo y la página |
| `--add-files` | **agregar** pistas a un item que ya existe en archive.org |
| `--update` | el show ya existe en `data/shows.yml`: lo actualiza sin perder los textos viejos de las pistas |
| `--build` | corre `hugo --minify --gc` al final y muestra los warnings |
| `--wait N` | minutos de espera por los derivados (default 30) |

## Agregar pistas a un show que ya está subido

Si el item ya existe en archive.org y lo que falta son pistas (un set nuevo de
una banda, una toma mejor, un encore), `--add-files` las sube **al item
existente** y después actualiza el catálogo:

```bash
python3 upload-recital.py --add-files
```

La numeración de los archivos sigue desde el final: si el item ya tiene 5
pistas, las nuevas se llaman `06 - ...`, `07 - ...`. Los nombres de archivo
que ya están no se tocan. En este modo no se manda metadata: la del item no
cambia.

## Qué NO hace el script

- **No pisa una página que ya existe.** Las páginas tienen texto escrito a
  mano (links a Instagram, notas del show) y eso no se toca. Si el show ya
  tenía página, el script la deja como está y avisa qué players quedaron
  afuera, con el markdown listo para pegar:

  ```
  # Banda 3
  {{< track show="la-maga/festimaga5" track="banda-3" >}}
  ```

- **No cambia el título del catálogo** de un show existente: está cuidado a
  mano. Las bandas sí las manda el `recital.txt`, y si difieren se avisa.

- **No borra ni modifica los masters.** Se copian a un temporal con el nombre
  canónico y se sube desde ahí.

- **No publica la página si la fecha del show es futura.** Hugo tiene
  `buildFuture` apagado, así que una página con fecha de mañana no sale hasta
  que llega. Para un show ya happened, funciona.

## Requisitos

- La CLI `ia` de archive.org, autenticada con la cuenta del sitio
  (`escalofrioexistencial@tuta.io`). Se verifica con `ia configure --whoami`.
  La config vive en `~/.config/internetarchive/ia.ini`.
- PyYAML.
- `hugo` extended, sólo si usás `--build`.

## Si algo sale mal

**"el item ya existe en archive.org"** — el identifier `live-<fecha>-<slug>`
ya está tomado. Se puede cambiar en el `recital.txt` con `identifier:`.

**"no hay audios para subir"** — la carpeta no tiene `.wav`/`.flac`/`.mp3`, o
el `recital.txt` no los lista y no hay archivos que entre.

**"no pude saber de qué banda es ..."** — falta el `tracks:` del `recital.txt`
o el nombre del archivo no contiene el nombre de la banda. El error dice
exactamente qué línea agregar.

**El sync no matchea** — casi siempre es la fecha: el item tiene una y el
catálogo otra. El script lo avisa con los dos valores. Se arregla con una
entrada en `OVERRIDES` (`scripts/sync-archive.py`).

**"el item ya existe en archive.org"** — usá `--add-files` si querés agregarle
pistas, o `--skip-upload` si sólo falta la entrada del catálogo.

**La página no aparece en el sitio** — mirá la fecha: si es futura, Hugo no la
publica. Si ya pasó, fijate si tiene `featured.*` (sin él, la página no entra
al archivo de `/flyers/`).

**Los derivados no llegan a tiempo** — archive.org deriva en background y con
masters de 1 GB puede tardar. El script avisa y sigue: el catálogo puede usar
el `.wav` directamente. Cuando terminen, se completa con:

```bash
python3 scripts/sync-archive.py --show <venue>/<show> --refresh --write
```

**El build de Hugo se cae con `failed to resize image`** — el flyer no es una
imagen de verdad (está corrupto o tiene otra extensión). El script chequea los
bytes mágicos antes de copiarlo, pero si el archivo se rompe después, el error
aparece en el build.

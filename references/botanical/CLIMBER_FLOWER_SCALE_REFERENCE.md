# Climber flower scale reference

Production scale lock for **Solandra maxima** and **Aristolochia macrophylla**. All Unreal dimensions assume **1 uu = 1 cm**.

## Measurement rule

Measure the **flower body**, not the full texture quad, transparent padding, pedicel, or flower stalk.

- **Solandra:** measure the corolla along its axis from the calyx/throat junction to the furthest reflexed rim/lobe.
- **Aristolochia:** measure the bent perianth body from the base of the utricle through the tube to the limb/mouth. Do not include the 3–7 cm peduncle documented by Flora of North America.

## Solandra maxima

### Source-grounded dimensions

- Corolla: **15–24 cm long**.
- Expanded cup/rim: approximately **10–15 cm wide**; other descriptions give rounded lobes spanning **8–15 cm**.
- Botany Brisbane breaks the corolla into a narrow tubular base around **10 cm** plus an expanded cup around **8 cm**, with reflexed lobes around **6 cm**.
- Mature leaf blade: around **20 × 10 cm** in Botany Brisbane; broader summaries commonly give **5–18 × 2–9 cm**.

### Production lock

- Ordinary open cups: **18–22 cm corolla length**.
- Full natural variation: **15–24 cm**.
- Natural maximum to use in the build: **24–25 cm**, not 34 cm.
- Rim width: **10–15 cm**.
- Buds: **12–20 cm** flower body, depending on maturity.

The mature open cup should read as approximately the **same length as a mature Solandra leaf blade**, commonly about **0.9–1.2× leaf length**. It is the large architectural bloom in this composition.

### Committed card conversion

In `solandra_maxima_flower_open_1024.png`, the corolla body occupies approximately **65.4% of the full texture width** and **74.4% of the opaque-content width**.

If Claude scales the **full 1024 quad width**:

- 15 cm corolla → **22.9 uu quad width**
- 18 cm corolla → **27.5 uu quad width**
- 22 cm corolla → **33.6 uu quad width**
- 24 cm corolla → **36.7 uu quad width**

Therefore the current 14–34 cm full-card range produces only about **9.2–22.2 cm of actual corolla**. The low end is substantially too small; the top end is normal. Use approximately **28–37 uu full-quad width**, with a center near **31–34 uu**, if this committed card is the geometry source.

## Aristolochia macrophylla

### Source-grounded dimensions

Flora of North America documents the flower as separate bent components:

- pendent utricle: **0.5–1.5 cm** long and **0.8–1 cm** wide;
- curved/bent cylindrical tube: **1–3 cm** long and **0.3–0.5 cm** wide;
- three limb lobes: **1.5–2 × 1.5–2 cm**;
- peduncle: **3–7 cm**, explicitly not part of the flower-body measurement.

*Trees and Shrubs Online* gives the complete perianth as **1–1.5 inches (2.5–3.8 cm) long**, with the brown-purple border at the mouth **0.5–0.75 inches (1.3–1.9 cm) across**. Common horticultural summaries round the flower to approximately **5 cm**.

### Production lock

- Ordinary pipe flower body: **3–4 cm**.
- Full natural production range: **2.5–5 cm**.
- Use **5 cm as a generous natural production maximum**, not as a formally documented taxonomic maximum.
- Mouth/limb spread: approximately **1.3–2 cm**.
- Deliberate VERDANT warmth-zone mutation may reach **5–7 cm**, but must be labelled and localized as mutation.

A normal pipe flower is only around **0.10–0.25× the length of a mature 15–30 cm leaf** and is commonly hidden beneath it. It is not a second architectural flower competing with Solandra.

### Committed card conversion

In `aristolochia_pipe_flower_1024.png`, the perianth body occupies approximately **64.6% of the full texture width** and **77.5% of the opaque-content width**.

If Claude scales the **full 1024 quad width**:

- 2.5 cm body → **3.9 uu quad width**
- 3 cm body → **4.6 uu quad width**
- 4 cm body → **6.2 uu quad width**
- 5 cm body → **7.7 uu quad width**
- 7 cm mutated body → **10.8 uu quad width**

The current 8–20 cm full-card range produces about **5.2–12.9 cm of actual flower body**. Its low end is already at the natural maximum; the high end is several times too large. Use approximately **4.6–7.7 uu full-quad width** for normal flowers and no more than **10.8 uu** for localized mutation.

## Compositional conclusion

The correction is deliberately asymmetric:

- **Scale Solandra up** from the low end of the current card range. Most hero cups should carry an actual 18–22 cm corolla.
- **Scale Aristolochia down**, unless a specific instance belongs to the mutation zone. A normal 3–5 cm bent pipe should disappear under a 15–30 cm heart-shaped leaf.
- At equal biological scale, a Solandra corolla is roughly **4–7× longer** than a normal Aristolochia perianth body and dramatically wider at the rim.

Do not compensate for concealed Aristolochia flowers by enlarging them. Reveal selected instances through placement, leaf gaps, warm rim lighting, and the explicit mutation subset.

## Sources

- Botany Brisbane, *Solandra maxima* — tube, cup, rim/lobe and mature-leaf measurements: <https://www.botanybrisbane.com/plants/solanaceae/solandra/solandra-maxima/>
- *Solandra maxima* morphology summary — corolla 15–24 cm and lobes 8–15 cm wide: <https://en.wikipedia.org/wiki/Solandra_maxima>
- Flora of North America via eFloras, *Aristolochia macrophylla* — utricle, tube, limb and peduncle component measurements: <http://www.efloras.org/florataxon.aspx?flora_id=1&taxon_id=233500160>
- *Trees and Shrubs Online*, *Aristolochia macrophylla* — complete perianth and mouth dimensions: <https://www.treesandshrubsonline.org/articles/aristolochia/aristolochia-macrophylla/>
- NC State Extension, *Aristolochia macrophylla* — horticultural flower-size category and concealed habit: <https://plants.ces.ncsu.edu/plants/aristolochia-macrophylla/>

### Evidence labels

- Exact published ranges above are **source-grounded**.
- “Ordinary,” “production lock,” card transforms, and the 5–7 cm mutation range are **VERDANT implementation decisions** derived from those ranges.
- The 5 cm Aristolochia natural ceiling is a **conservative production maximum**, not a proven species-wide absolute maximum.
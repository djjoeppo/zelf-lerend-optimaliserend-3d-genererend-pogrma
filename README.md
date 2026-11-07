# Zelflerend Optimalisatieprogramma voor Luidsprekerconussen
*(Multi-Fidelity Genetic Algorithm & Free-Air Acoustic Simulation)*

Een geavanceerd ontwerpprogramma om 3D-printbare luidsprekerconussen automatisch te ontwerpen, testen en optimaliseren met behulp van een multi-fidelity genetisch algoritme (GA) en natuurkundige/akoestische simulaties in vrije lucht (free-air).

---

## 🎯 Doel & Werking

Het programma optimaliseert conusontwerpen voor een vooraf gekozen luidsprekermotor (spreekspoel, magneetkracht $Bl$, bewegende massa $M_{vc}$, spider/surround compliantie $C_{ms}$, demping $R_{ms}$).

### Staged Multi-Fidelity Optimalisatie
1. **Invoer & Sandbox Definitie:**
   - Maximale conusdiameter en maximale hoogte (sandbox).
   - Minimale wanddikte (standaard 0,4 mm - harde afkeurregel).
   - Overhangcontrole (instelbare hoek, schakelbaar AAN/UIT).
   - Voice-coil montagekraag (collar cilinder) voor stevige verlijming.
   - Montageflens interface upload (STL) voor spider/surround compatibiliteit.
   - Vermijdingszones (Keep-out zones) ter voorkoming van botsingen bij maximale conusuitslag.
2. **Fase 1: Snelle Schifting (Fast Screening):**
   - Lumped-parameter zuigermodel.
   - Snelle afkeur van niet-maakbare conussen (te dunne wand, botsingen, te extreme overhangs).
   - Schatting van conusmassa, resonantiefrequentie ($F_s$), referentiegevoeligheid (SPL dB @ 1W/1m) en stijfheidsindex.
3. **Fase 2: Verfijning (Refinement):**
   - Analyse van conus elastische schaalmodi en buiggolven (breakup modes).
   - Berekening van free-air frequentierespons curve ($20\text{ Hz} - 20\text{ kHz}$) en lineariteitsrimpel.
4. **Inspectie & Productie:**
   - Interactieve 3D inspectie (Three.js) met orbit rotatie, zoom, wireframe en 3/4 doorsnedeweergave.
   - 2D conuswand doorsnedeprofiel en wanddikteverloop $t(r)$.
   - Directe STL export voor slicers zoals Bambu Studio, PrusaSlicer en Cura.

---

## 🚀 Installatie & Starten

### Vereisten
- Python 3.10 of nieuwer
- Node.js 18 of nieuwer

### Snel starten (1-klik launcher)
Het programma kan eenvoudig in één keer worden opgestart via `main.py`. Dit bouwt indien nodig de frontend, start de server en opent direct automatisch uw browser:

```bash
# 1. Installeer dependencies (eenmalig)
pip install -r requirements.txt
cd frontend && npm install && cd ..

# 2. Start de studio
python main.py
```

De studio opent direct op `http://127.0.0.1:8000`.

### Ontwikkelmodus (Optioneel)
Voor actieve frontend ontwikkeling met hot-reloading:
```bash
# Terminal 1: Backend
python3 -m uvicorn backend.cone_opt.api:app --reload

# Terminal 2: Frontend
cd frontend && npm run dev
```

---

## 🧪 Tests Uitvoeren

De testsuite controleert alle fysische modellen, geometriegeneratie, harde printbaarheidsgrenzen en de FastAPI endpoints:

```bash
PYTHONPATH=. pytest tests/ -v
```

---

## 📐 Belangrijke Aandachtspunten
- **Free-air simulaties:** De akoestische simulatie richt zich op de conus in vrije lucht (zonder kast). De uiteindelijke prestaties in een basreflex- of gesloten behuizing dienen na het printen gemeten en afgestemd te worden (bijv. via REW).
- **3D-printen:** Gebruik een nozzle van 0,4 mm of 0,25 mm en 100% infill voor de conuswand (massieve perimeters).

---

## 📄 Licentie
Dit project is gelicenseerd onder de MIT-licentie.

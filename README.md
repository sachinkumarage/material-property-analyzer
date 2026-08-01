# Material Property Analyzer

A beginner-friendly Python tool for exploring and comparing engineering
materials (metals, composites, wood, ceramics, polymers) using real
mechanical properties like density, strength, and stiffness.

It reads a CSV database of materials, calculates the **strength-to-weight
ratio** (and a few other useful engineering ratios), ranks and compares
materials, and generates matplotlib charts to visualize the results.

## Why this matters (materials engineering 101)

When engineers choose a material for a part, "strongest" is rarely the
right question - it's usually "strongest **for its weight**". A material
that is very strong but very dense (like some steels) can end up making a
heavier part than a lighter, moderately strong material like aluminum or
carbon fiber.

The key formula this project is built around:

```
strength-to-weight ratio = strength / density
```

This is also called **specific strength**. A higher value means the
material delivers more strength per gram - exactly what you want for
things like aircraft, bicycles, rockets, and drones, where every gram
counts. The same idea applies to **specific stiffness**
(`elastic modulus / density`), which matters when a part needs to resist
bending rather than just avoid breaking.

## Part 2: Advanced Material Selection

Part 1 lets you rank and compare materials by a single property at a
time. Part 2 adds a full **material selection system** that mirrors how
engineers actually choose materials: first **filter** out anything that
can't do the job, then **rank** what's left by how well it fits several
competing goals at once (strength, stiffness, and cost together).

### New features

- **`src/selection_engine.py`** - filters materials by hard requirements
  (max density, min strength, max cost, category, ...) and ranks the
  survivors using a weighted score. Includes ready-made goal presets:
  - `lightweight_strength` - best strength-to-weight ratio (aircraft,
    drones, bike frames)
  - `rigid_structure` - best stiffness-to-weight ratio (beams,
    brackets, tooling)
  - `budget_friendly` - most strength per dollar (mass-produced parts)
  - `balanced` - an even mix of all three
- **`src/scoring.py`** - normalizes engineering ratios onto a common
  0-100 scale and combines them into one overall **match score** using
  a weighted decision matrix. Includes dedicated **specific strength**
  and **specific stiffness** scores.
- **`src/cli.py`** - an interactive command-line interface: pick a
  selection goal and optional requirements by answering plain-English
  prompts, and get back a ranked shortlist - no Python required.

## Project structure

```
material-property-analyzer/
├── data/
│   └── materials.csv          # Sample materials database
├── output/                    # Generated charts land here (gitignored)
├── src/
│   ├── __init__.py
│   ├── database.py            # Load/query/add materials from CSV
│   ├── calculations.py        # Strength-to-weight & other formulas
│   ├── comparator.py          # Rank and compare materials
│   ├── visualizer.py          # matplotlib chart generation
│   ├── scoring.py             # Part 2: 0-100 scores & weighted match score
│   ├── selection_engine.py    # Part 2: filter + rank materials by goal
│   └── cli.py                 # Part 2: interactive material selector
├── main.py                    # Run the full analysis end-to-end
├── requirements.txt
├── .gitignore
└── README.md
```

## Getting started

1. **Create a virtual environment (recommended):**

   ```bash
   python -m venv venv
   source venv/bin/activate   # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

3. **Run the analyzer:**

   ```bash
   python main.py
   ```

   This will print material rankings and comparisons to the terminal,
   save three charts into `output/`, and finish with a demo of the Part 2
   selection engine:

   - `strength_to_weight_ranking.png` - bar chart ranking materials by
     specific strength
   - `strength_vs_density.png` - a classic "materials selection" scatter
     chart (strength vs. density, colored by category)
   - `material_comparison.png` - a normalized side-by-side comparison of
     hand-picked materials

4. **Or, pick a material interactively (Part 2):**

   ```bash
   python main.py --select
   ```

   This skips the demo report and launches an interactive prompt where
   you choose a selection goal (e.g. "lightweight & strong") and
   optional requirements (max cost, max density, category, ...), then
   prints a ranked shortlist of the best-matching materials. You can
   also run it directly with `python -m src.cli`.

## The materials database (`data/materials.csv`)

Each row describes one material with these columns:

| Column | Meaning |
|---|---|
| `name` | Material name |
| `category` | Metal, Composite, Wood, Ceramic, or Polymer |
| `density_g_cm3` | Density in grams per cubic centimetre |
| `tensile_strength_mpa` | Ultimate tensile strength (MPa) - stress at which the material breaks |
| `yield_strength_mpa` | Yield strength (MPa) - stress at which the material permanently deforms |
| `elastic_modulus_gpa` | Young's modulus (GPa) - a measure of stiffness |
| `cost_usd_per_kg` | Approximate raw material cost |

Values are realistic approximations meant for learning and experimentation,
not for real engineering design work.

### Adding your own materials

You can edit `data/materials.csv` directly in a spreadsheet program, or use
Python:

```python
from src.database import MaterialDatabase

db = MaterialDatabase("data/materials.csv")
db.add_material(
    name="Bamboo",
    category="Wood",
    density_g_cm3=0.7,
    tensile_strength_mpa=140,
    yield_strength_mpa=100,
    elastic_modulus_gpa=20,
    cost_usd_per_kg=1.2,
)
db.save()  # writes back to data/materials.csv
```

## Using the modules yourself

```python
from src.database import MaterialDatabase
from src.comparator import MaterialComparator

db = MaterialDatabase("data/materials.csv")
comparator = MaterialComparator(db.data)

# Rank all materials by strength-to-weight ratio
print(comparator.best_strength_to_weight(top_n=5))

# Compare specific materials side by side
print(comparator.compare(["Aluminum 6061-T6", "Titanium Ti-6Al-4V"]))
```

### Using the Part 2 selection engine

```python
from src.database import MaterialDatabase
from src.selection_engine import SelectionEngine

db = MaterialDatabase("data/materials.csv")
engine = SelectionEngine(db.data)

# Use a ready-made goal preset ("lightweight_strength", "rigid_structure",
# "budget_friendly", or "balanced") plus optional hard requirements.
shortlist = engine.select(
    goal="lightweight_strength",
    categories=["Metal", "Composite"],
    max_cost=25.0,       # USD/kg
    max_density=5.0,     # g/cm3
    top_n=5,
)
print(shortlist)

# Or supply your own custom weights instead of a preset - weights don't
# need to add up to 1, they're normalized automatically.
custom_shortlist = engine.select(
    weights={
        "specific_strength_score": 0.5,
        "specific_stiffness_score": 0.3,
        "cost_score": 0.2,
    },
    max_cost=10.0,
)
print(custom_shortlist)
```

## Key formulas used

- **Specific strength (strength-to-weight ratio):** `strength / density`
  - Higher is better when minimizing weight matters most.
- **Specific stiffness:** `elastic_modulus / density`
  - Higher is better when resisting bending/flex matters most.
- **Cost per unit strength:** `cost_per_kg / tensile_strength`
  - Lower is better when budget is the priority.

See the comments in `src/calculations.py` for a deeper explanation of each
concept.

### Part 2 formulas: normalized scoring & weighted matching

The selection engine can't compare "MPa per g/cm3" directly against "USD
per MPa" - they're different units. It solves this in two steps, both
explained in detail in `src/scoring.py`:

**1. Normalize each property onto a 0-100 scale** (min-max normalization):

```
score = 100 * (value - worst) / (best - worst)
```

The best material for that property scores 100, the worst scores 0, and
everything else falls proportionally in between. For "lower is better"
properties like cost, the direction is flipped so the *cheapest* material
still scores highest.

**2. Combine scores into one overall match score** (a weighted decision
matrix):

```
match_score = (strength_score * strength_weight
             + stiffness_score * stiffness_weight
             + cost_score * cost_weight)
             / (strength_weight + stiffness_weight + cost_weight)
```

Each weight represents how much that property matters for the part
you're designing. A bike frame might weight specific strength heavily
and barely care about cost; a mass-produced bracket might do the
opposite. Changing the weights changes the ranking - that's the whole
point of a weighted decision matrix.

## Learning goals

This project is intentionally kept simple and heavily commented so it can
be used as a learning tool for:

- Reading/writing CSV data with `pandas`
- Structuring a small Python project into modules
- Applying basic engineering formulas in code
- Creating charts with `matplotlib`
- Normalizing and combining metrics with a weighted decision matrix
- Building a simple interactive command-line interface

Feel free to extend it further - more materials, more properties (fatigue
strength, thermal conductivity, corrosion resistance), or saving/loading
custom weight presets would all be natural next steps.

# Material Property Analyzer

A beginner-friendly Python tool for exploring and comparing engineering
materials - steels, aluminum and titanium alloys, ceramics, polymers,
composites, wood, and more - using real mechanical, thermal, electrical,
and cost properties.

It reads a CSV database of over 100 materials across 17 categories,
calculates the **strength-to-weight ratio** (and a few other useful
engineering ratios), ranks and compares materials, and generates
matplotlib charts to visualize the results.

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

The database contains **109 engineering materials across 17 categories**:

Carbon Steels, Stainless Steels, Tool Steels, Aluminum Alloys, Titanium
Alloys, Magnesium Alloys, Copper Alloys, Nickel Alloys, Cast Irons,
Ceramics, Glass, Polymers, Elastomers, Composites, Wood, Concrete, and
Natural Materials.

Each row describes one material with these columns:

| Column | Meaning | Units / notes |
|---|---|---|
| `name` | Material name, e.g. "Aluminum 6061-T6" | - |
| `category` | One of the 17 categories listed above | - |
| `density_g_cm3` | Mass per unit volume | g/cm³ |
| `yield_strength_mpa` | Stress at which the material starts to permanently deform | MPa |
| `tensile_strength_mpa` | Ultimate tensile strength - the stress at which the material breaks | MPa |
| `elastic_modulus_gpa` | Young's modulus - stiffness, i.e. resistance to elastic stretching/bending | GPa |
| `poisson_ratio` | How much a material narrows sideways when stretched lengthwise | unitless, typically 0-0.5 |
| `hardness_value` | Resistance to surface indentation/scratching | see `hardness_scale` |
| `hardness_scale` | Which hardness scale `hardness_value` is measured on | HB, HRC, HV, Shore A, Shore D, Mohs, Janka, or Barcol - see below |
| `thermal_conductivity_w_mk` | How well the material conducts heat | W/(m·K) |
| `electrical_conductivity_percent_iacs` | Electrical conductivity relative to pure annealed copper | %IACS (copper = 100%, insulators ≈ 0%) |
| `melting_point_c` | Melting point, or an approximate softening/decomposition temperature for materials without a sharp melting point (see note below) | °C |
| `fatigue_strength_mpa` | Approximate stress the material can survive for ~10 million load cycles without breaking | MPa |
| `cost_usd_per_kg` | Approximate raw material cost | USD/kg |
| `corrosion_resistance` | Rough qualitative rating | Poor, Fair, Good, or Excellent |

Loading the database through `src/database.py` also gives you a derived
`relative_cost_index` column (via `add_calculated_columns`) - see
[Key formulas used](#key-formulas-used) below.

### About the hardness scales

Different material families are conventionally measured on different
hardness scales, so this project keeps the raw scale alongside the
value instead of forcing everything onto one number:

| Scale | Used for | Typical range in this dataset |
|---|---|---|
| **HB** (Brinell) | Most metals (steels, aluminum, copper, magnesium, nickel, cast iron) | ~20-500 |
| **HRC** (Rockwell C) | Hardened tool steels and some hardened alloys | ~40-65 |
| **HV** (Vickers) | Technical ceramics (too hard for a Brinell indenter) | ~1,200-3,000 |
| **Shore D** | Rigid plastics | ~45-90 |
| **Shore A** | Soft rubbers/elastomers, and a few soft natural materials | ~30-85 |
| **Mohs** | Glass, concrete, and other mineral-based brittle materials | ~3-7 |
| **Janka** (lbf) | Wood - the force needed to embed a steel ball halfway into the wood | ~90-1,450 |
| **Barcol** | Fiber-reinforced composites | ~40-60 |

### A note on data sources and accuracy

Every value in `data/materials.csv` is an **approximate, representative
figure** drawn from commonly used materials-engineering references
(handbook-style typical values, e.g. ASM Handbook-style data and
manufacturer datasheet ranges), not a certified test result. Real
material properties vary by supplier, heat treatment, temper, and test
method. A few columns need extra context because not every material
family fits neatly into "strength" and "melting point":

- **Brittle materials** (ceramics, glass, cast irons like White Cast
  Iron) don't have a true yield point - they crack instead of bending.
  For these rows, `yield_strength_mpa` is set equal to
  `tensile_strength_mpa` (approximated by flexural/fracture strength).
- **Materials without a sharp melting point** - polymers, elastomers,
  wood, concrete, and natural materials - don't melt the way a metal
  does. `melting_point_c` for these rows is an approximate
  softening, decomposition, or ignition temperature instead.
- **This data is for learning and experimentation only** - do not use
  it for real engineering design work. Always consult a certified
  datasheet or run your own testing for anything load-bearing.

### Adding your own materials

You can edit `data/materials.csv` directly in a spreadsheet program, or use
Python:

```python
from src.database import MaterialDatabase

db = MaterialDatabase("data/materials.csv")
db.add_material(
    name="Rattan (Bamboo Cane)",
    category="Wood",
    density_g_cm3=0.7,
    yield_strength_mpa=100,
    tensile_strength_mpa=140,
    elastic_modulus_gpa=20,
    poisson_ratio=0.3,
    hardness_value=1000,
    hardness_scale="Janka",
    thermal_conductivity_w_mk=0.15,
    electrical_conductivity_percent_iacs=0,
    melting_point_c=300,
    fatigue_strength_mpa=40,
    cost_usd_per_kg=1.2,
    corrosion_resistance="Fair",
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
    categories=["Aluminum Alloys", "Titanium Alloys", "Composites"],
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
- **Relative cost index:** `cost_per_kg / 1.0 USD` (the approximate price
  of plain structural carbon steel)
  - A value of 20 means "about 20x the price of basic carbon steel" -
    handy for comparing cost across very differently priced materials
    (e.g. wood vs. titanium) without caring about market price swings.

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
- Working with a larger, multi-property real-world-style dataset

Feel free to extend it further - more materials, temperature-dependent
properties, saving/loading custom weight presets, or scoring by thermal
or electrical conductivity would all be natural next steps.

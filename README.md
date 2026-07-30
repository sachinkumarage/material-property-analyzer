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
│   └── visualizer.py          # matplotlib chart generation
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

   This will print material rankings and comparisons to the terminal, and
   save three charts into `output/`:

   - `strength_to_weight_ranking.png` - bar chart ranking materials by
     specific strength
   - `strength_vs_density.png` - a classic "materials selection" scatter
     chart (strength vs. density, colored by category)
   - `material_comparison.png` - a normalized side-by-side comparison of
     hand-picked materials

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

## Key formulas used

- **Specific strength (strength-to-weight ratio):** `strength / density`
  - Higher is better when minimizing weight matters most.
- **Specific stiffness:** `elastic_modulus / density`
  - Higher is better when resisting bending/flex matters most.
- **Cost per unit strength:** `cost_per_kg / tensile_strength`
  - Lower is better when budget is the priority.

See the comments in `src/calculations.py` for a deeper explanation of each
concept.

## Learning goals

This project is intentionally kept simple and heavily commented so it can
be used as a learning tool for:

- Reading/writing CSV data with `pandas`
- Structuring a small Python project into modules
- Applying basic engineering formulas in code
- Creating charts with `matplotlib`

Feel free to extend it - more materials, more properties (fatigue strength,
thermal conductivity, corrosion resistance), or a simple command-line
interface for interactive queries would all be natural next steps.

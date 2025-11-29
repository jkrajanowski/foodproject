# FlavorGraph AI

FlavorGraph AI is an interactive ingredient graph and recipe explorer built on the  
[`AkashPS11/recipes_data_food.com`](https://huggingface.co/datasets/AkashPS11/recipes_data_food.com) dataset.

It constructs an ingredient co-occurrence network from real recipes and visualizes it in an interactive PyVis/vis.js interface. The system includes multiple visualization modes, filtering controls, a recipe explorer panel, and a modal viewer for full recipe details.

---

## Features

### Interactive Ingredient Graph
- Nodes represent ingredients.
- Edges represent co-occurrence in recipes.
- Graph is centered on a selected ingredient to maintain readability.
- Selecting exactly one ingredient hides all unrelated nodes to focus the local neighborhood.

### Visualization Modes
Switch between:
- Popularity (ingredient frequency)
- Calories (average calories in recipes containing the ingredient)
- Rating (average user rating)
- Clusters (community detection using modularity)

Both node color and node size change according to the selected mode.

### Graph Controls
A control panel is auto-injected into the generated HTML file. It provides:
- Ingredient search bar
- Minimum co-occurrence slider
- Color mode buttons
- Node info panel with computed statistics

### Recipe Explorer
- Clicking an ingredient displays recipes that include it.
- Ctrl+click allows selecting multiple ingredients.
- Only recipes that include all selected ingredients are displayed.
- Recipes appear in a scrollable panel on the right.

### Modal Recipe Viewer
Selecting a recipe opens a centered modal displaying:
- Recipe title
- Ingredient list
- Instructions

Support for dataset image URLs will be added in a future update.

### Modular Codebase

src/
visualize_interactive.py # graph construction and HTML/JS interface injection
recipes_data.py # dataset loading utilities and helpers
ui.py # JavaScript and HTML generation for the browser interface
flavorgraph_ai.py # ingredient graph construction logic

---

## Installation

### 1. Clone the repository

git clone https://github.com/jkrajanowski/foodproject
cd flavorgraph-ai


### 2. Create and activate a virtual environment (Windows)

python -m venv .venv
..venv\Scripts\activate


### 3. Install dependencies

pip install -r requirements.txt


## Usage

Run the main script:

python src/visualize_interactive.py


Example input:

chicken

This generates an HTML file such as:

flavorgraph_chicken.html

Open the file in your browser to explore the graph.

---

## Controls and Interaction

### Color Mode Buttons
Switches node colors and sizes based on popularity, calories, rating, or cluster membership.

### Ingredient Search
Centers and zooms the graph on a matching ingredient.

### Co-Occurrence Slider
Filters out edges with weights (co-occurrence counts) below the chosen threshold.

### Node Interaction
- Click a node to view statistics and related recipes.
- Ctrl+click multiple nodes to filter recipes that include all selected ingredients.
- Clicking empty space clears the selection.

### Recipe Panel and Modal
- A list of matching recipes appears in a right-side panel.
- Clicking a recipe opens a detailed modal view.

---

## Dataset

This project uses the public dataset located at:  
https://huggingface.co/datasets/AkashPS11/recipes_data_food.com

The dataset includes:
- Recipe titles
- Ingredient lists
- Instructions
- Ratings
- Calorie counts
- Optional image URLs (multiple formats)

Image display support will be included in a future update.

---

## Architecture Overview

### Ingredient Graph Construction
1. Load up to `max_recipes` recipes from the dataset.
2. Normalize ingredient names.
3. For each recipe:
   - Add ingredient nodes.
   - Add weighted edges between ingredients that co-occur.
4. Compute:
   - Popularity (number of recipes containing each ingredient)
   - Average calories
   - Average ratings
5. Detect ingredient clusters using greedy modularity.

### Visualization Layer
A PyVis-generated vis.js network provides:
- Dynamic node color and size updates
- Hover tooltips
- Selectable nodes and edges
- Node visibility filtering based on selection

### Frontend Layer
A custom JavaScript interface is injected into the HTML output, enabling:
- Search
- Filtering
- Mode switching
- Recipe panel rendering
- Modal display for recipe details

---

## Roadmap

Planned improvements include:
- Displaying recipe images
- Global ingredient graph mode (not centered on a single ingredient)
- Advanced clustering (Louvain/Leiden)
- Exporting selected recipes to a mini cookbook
- Ingredient similarity scoring using embeddings
- Browser-hosted web application with API backend

---

## License

MIT License.
from __future__ import annotations

from pathlib import Path

import math
import networkx as nx
from pyvis.network import Network

from flavorgraph_ai import build_graph, normalize_ing
from recipes_data import load_recipes_for_subgraph
from ui import inject_controls, inject_recipe_data


# ---------- Color helpers & cluster palette ----------

def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def _gradient(value: float, vmin: float, vmax: float,
              low_color: str, high_color: str) -> str:
    """Generic 2-color gradient."""
    if vmax <= vmin:
        return "#7f8c8d"  # fallback gray

    ratio = (value - vmin) / (vmax - vmin)
    ratio = max(0.0, min(1.0, ratio))

    r1, g1, b1 = _hex_to_rgb(low_color)
    r2, g2, b2 = _hex_to_rgb(high_color)

    r = int(r1 + (r2 - r1) * ratio)
    g = int(g1 + (g2 - g1) * ratio)
    b = int(b1 + (b2 - b1) * ratio)

    return _rgb_to_hex((r, g, b))


def color_popularity(count: int, cmin: int, cmax: int) -> str:
    # Blue -> Pink
    return _gradient(count, cmin, cmax, "#3498db", "#e91e63")


def color_calories(avg_cal: float, amin: float, amax: float) -> str:
    # Green (light) -> Red (heavy)
    return _gradient(avg_cal, amin, amax, "#2ecc71", "#e74c3c")


def color_rating(avg_rating: float, rmin: float, rmax: float) -> str:
    # Gray (low) -> white (high) (you can tweak)
    return _gradient(avg_rating, rmin, rmax, "#7f8c8d", "#ffffff")


CLUSTER_PALETTE = [
    "#e74c3c",  # red
    "#3498db",  # blue
    "#2ecc71",  # green
    "#9b59b6",  # purple
    "#f1c40f",  # yellow
    "#1abc9c",  # teal
    "#e67e22",  # orange
    "#ff6b81",  # pink
    "#16a085",  # dark teal
    "#95a5a6",  # gray
]


def color_cluster(cluster_id: int) -> str:
    return CLUSTER_PALETTE[cluster_id % len(CLUSTER_PALETTE)]


# ---------- Graph helpers ----------

def build_neighborhood_subgraph(
    G: nx.Graph,
    center_ing: str,
    max_neighbors: int = 40,
) -> nx.Graph:
    """
    Return a subgraph consisting of the center ingredient and up to
    max_neighbors of its neighbors.
    """
    center_ing = normalize_ing(center_ing)

    if center_ing not in G:
        raise ValueError(f"Ingredient '{center_ing}' not found in graph.")

    neighbors = list(G.neighbors(center_ing))
    if not neighbors:
        raise ValueError(f"No neighbors found for '{center_ing}'.")

    neighbors = neighbors[:max_neighbors]
    sub_nodes = [center_ing] + neighbors
    H = G.subgraph(sub_nodes).copy()
    return H


def visualize_interactive(
    center_ing: str,
    max_recipes: int = 300000,
    max_neighbors: int = 80,
    output_html: str | None = None,
):
    """
    Build the ingredient graph and visualize the local neighborhood of
    center_ing as an interactive HTML graph.
    """
    center_ing = normalize_ing(center_ing)
    print(f"Building graph from first {max_recipes} recipes...")
    G = build_graph(max_recipes=max_recipes)

    print(f"Extracting neighborhood for '{center_ing}'...")
    H = build_neighborhood_subgraph(G, center_ing, max_neighbors=max_neighbors)

    print(
        f"Subgraph: {H.number_of_nodes()} nodes, {H.number_of_edges()} edges."
    )

    # --- Community detection (clusters) ---
    from networkx.algorithms import community

    communities = list(community.greedy_modularity_communities(H))
    cluster_map: dict[str, int] = {}
    for cid, com in enumerate(communities):
        for n in com:
            cluster_map[n] = cid

    # Stats for gradients
    counts: list[int] = []
    cals: list[float] = []
    ratings: list[float] = []
    for n in H.nodes():
        data = G.nodes[n]
        counts.append(data.get("count", 0) or 0)
        cal = data.get("avg_calories", 0.0) or 0.0
        rat = data.get("avg_rating", 0.0) or 0.0
        cals.append(cal)
        ratings.append(rat)

    cmin = min(counts) if counts else 0
    cmax = max(counts) if counts else 1
    amin = min(cals) if cals else 0.0
    amax = max(cals) if cals else 1.0
    rmin = min(ratings) if ratings else 0.0
    rmax = max(ratings) if ratings else 5.0

    # --- Load recipes for this subgraph ---
    recipes, ing_to_recipes = load_recipes_for_subgraph(
        center_ing=center_ing,
        subgraph_nodes=list(H.nodes()),
        max_recipes=max_recipes,
    )
    print(f"Loaded {len(recipes)} recipes for this ingredient neighborhood.")

    if output_html is None:
        safe_name = center_ing.replace(" ", "_")
        output_html = f"flavorgraph_{safe_name}.html"

    net = Network(
        height="1000px",
        width="100%",
        bgcolor="#050816",
        font_color="white",
        notebook=False,
        directed=False,
    )

    # Physics layout
    net.barnes_hut()

    net.set_options("""
{
  "nodes": {
    "shape": "dot",
    "font": {
      "size": 22,
      "color": "#ffffff",
      "face": "arial",
      "strokeWidth": 2,
      "strokeColor": "#000000"
    },
    "borderWidth": 2,
    "shadow": true
  },
  "edges": {
    "color": {
      "color": "#4b5d7a",
      "highlight": "#ffffff"
    },
    "width": 1.5,
    "selectionWidth": 4,
    "smooth": false
  },
  "interaction": {
    "hover": true,
    "selectConnectedEdges": true,
    "hoverConnectedEdges": true,
    "multiselect": true
  },
  "physics": {
    "stabilization": {
      "iterations": 300
    },
    "barnesHut": {
      "gravitationalConstant": -15000,
      "springConstant": 0.01,
      "springLength": 200
    }
  }
}
""")

    # --- Add nodes with colors, sizes, and info ---
    for node in H.nodes():
        data = G.nodes[node]
        avg_cal = data.get("avg_calories", 0.0) or 0.0
        avg_rating = data.get("avg_rating", 0.0) or 0.0
        count = data.get("count", 0) or 0

        # Colors for each mode
        col_pop = color_popularity(count, cmin, cmax)
        col_cal = color_calories(avg_cal, amin, amax)
        col_rat = color_rating(avg_rating, rmin, rmax)

        # Cluster color
        cid = cluster_map.get(node, 0)
        col_clu = color_cluster(cid)

        # Default mode = popularity
        color = col_pop

        # --- Sizes for each mode ---

        # Popularity size: 18–40
        ratio_pop = count / cmax if cmax > 0 else 0.0
        size_pop_base = 18 + 22 * ratio_pop

        # Calories size: 18–40 (higher calories -> bigger)
        ratio_cal = 0.0
        if amax > amin:
            ratio_cal = (avg_cal - amin) / (amax - amin)
        ratio_cal = max(0.0, min(1.0, ratio_cal))
        size_cal_base = 18 + 22 * ratio_cal

        # Rating size: 18–40 (higher rating -> bigger)
        ratio_rat = 0.0
        if rmax > rmin:
            ratio_rat = (avg_rating - rmin) / (rmax - rmin)
        ratio_rat = max(0.0, min(1.0, ratio_rat))
        size_rat_base = 18 + 22 * ratio_rat

        # Cluster size: reuse popularity size
        size_clu_base = size_pop_base

        # Center node gets a bump in all modes
        if node == center_ing:
            size_pop = size_pop_base + 10
            size_cal = size_cal_base + 10
            size_rat = size_rat_base + 10
            size_clu = size_clu_base + 10
        else:
            size_pop = size_pop_base
            size_cal = size_cal_base
            size_rat = size_rat_base
            size_clu = size_clu_base

        # Default size = popularity size
        size = size_pop

        # Info panel + tooltip content
        info_html = (
            f"<b>{node}</b><br>"
            f"Cluster: {cid}<br>"
            f"Popularity (recipes): {count}<br>"
            f"Avg rating: {avg_rating:.2f}<br>"
            f"Avg calories: {avg_cal:.1f}"
        )

        net.add_node(
            node,
            label=node,
            color=color,        # initial (popularity)
            size=size,          # initial size (popularity)
            title=info_html,    # hover
            info_html=info_html,
            cluster_id=cid,
            popularity=count,
            avg_rating=avg_rating,
            avg_cal=avg_cal,
            color_pop=col_pop,
            color_cal=col_cal,
            color_rat=col_rat,
            color_clu=col_clu,
            size_pop=size_pop,
            size_cal=size_cal,
            size_rat=size_rat,
            size_clu=size_clu,
        )

    # --- Add edges with weight ---
    for src, dst, edata in H.edges(data=True):
        cooc = edata.get("cooc", 1)
        net.add_edge(src, dst, value=cooc)

    # --- Save & inject UI + data ---
    output_path = Path(output_html).resolve()
    print(f"Saving interactive graph to: {output_path}")

    net.write_html(str(output_path), notebook=False)

    inject_recipe_data(output_path, recipes, ing_to_recipes)
    inject_controls(output_path)

    print("Interactive graph saved with controls. Open this file in your browser:")
    print(output_path)


if __name__ == "__main__":
    ingredient = input("Ingredient to visualize (e.g. chicken, chocolate): ").strip()
    if not ingredient:
        print("No ingredient provided, exiting.")
    else:
        try:
            visualize_interactive(ingredient)
        except ValueError as e:
            print(f"Error: {e}")

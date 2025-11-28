import ast
import itertools
from typing import List, Dict

import networkx as nx
from datasets import load_dataset
from tqdm import tqdm


def r_vector_to_list(s: str) -> List[str]:
    """
    Convert strings like 'c("a", "b")' to ['a', 'b'].
    The dataset uses this R-like vector format.
    """
    if s is None:
        return []
    s = s.strip()
    if not s:
        return []
    if not s.startswith("c("):
        # sometimes it's just a single string
        return [s]
    # Drop leading 'c(' and trailing ')'
    inner = s[2:-1]
    py_like = "[" + inner + "]"
    try:
        return ast.literal_eval(py_like)
    except Exception:
        # Fallback: return raw
        return [s]


def normalize_ing(name: str) -> str:
    """Simple normalization for ingredient names."""
    return name.strip().lower()


def get_ingredients(row) -> List[str]:
    parts = r_vector_to_list(row.get("RecipeIngredientParts"))
    return [normalize_ing(p) for p in parts if p and isinstance(p, str)]


def build_graph(
    max_recipes: int = 50000,
) -> nx.Graph:
    """
    Build an ingredient co-occurrence graph from the HF dataset.

    Nodes: ingredients
      - count: how many recipes include this ingredient
      - rating_sum: sum of ratings of recipes including it
      - cal_sum: sum of calories of recipes including it

    Edges: (ingredient A, ingredient B)
      - cooc: how many recipes include both
      - rating_sum: sum of ratings of recipes including both
      - cal_sum: sum of calories of recipes including both
    """
    print("Loading dataset 'AkashPS11/recipes_data_food.com'...")
    ds = load_dataset("AkashPS11/recipes_data_food.com", split="train")

    G = nx.Graph()

    def add_recipe_to_graph(ingredients, rating=None, calories=None):
        unique_ings = list(set(ingredients))
        if len(unique_ings) < 2:
            return

        # Update nodes
        for ing in unique_ings:
            if not G.has_node(ing):
                G.add_node(ing, count=0, rating_sum=0.0, cal_sum=0.0)
            G.nodes[ing]["count"] += 1
            if rating is not None:
                try:
                    G.nodes[ing]["rating_sum"] += float(rating)
                except (TypeError, ValueError):
                    pass
            if calories is not None:
                try:
                    G.nodes[ing]["cal_sum"] += float(calories)
                except (TypeError, ValueError):
                    pass

        # Update edges
        for a, b in itertools.combinations(unique_ings, 2):
            if G.has_edge(a, b):
                G[a][b]["cooc"] += 1
            else:
                G.add_edge(a, b, cooc=1, rating_sum=0.0, cal_sum=0.0)
            if rating is not None:
                try:
                    G[a][b]["rating_sum"] += float(rating)
                except (TypeError, ValueError):
                    pass
            if calories is not None:
                try:
                    G[a][b]["cal_sum"] += float(calories)
                except (TypeError, ValueError):
                    pass

    # If dataset length is known, use it for tqdm; otherwise just use max_recipes
    total = min(max_recipes, len(ds)) if hasattr(ds, "__len__") else max_recipes
    print(f"Building ingredient graph from first {max_recipes} recipes...")
    for i, row in tqdm(enumerate(ds), total=total):
        if i >= max_recipes:
            break
        ings = get_ingredients(row)
        if len(ings) < 2:
            continue
        rating = row.get("AggregatedRating")
        calories = row.get("Calories")
        add_recipe_to_graph(ings, rating=rating, calories=calories)

    print("Computing average statistics per ingredient...")
    for ing, data in G.nodes(data=True):
        c = data.get("count", 0)
        if c > 0:
            rating_sum = data.get("rating_sum", 0.0)
            cal_sum = data.get("cal_sum", 0.0)
            data["avg_rating"] = rating_sum / c if rating_sum else 0.0
            data["avg_calories"] = cal_sum / c if cal_sum else 0.0
        else:
            data["avg_rating"] = 0.0
            data["avg_calories"] = 0.0

    print(f"Graph built: {G.number_of_nodes()} ingredients, {G.number_of_edges()} edges.")
    return G


def suggest_neighbors_scored(
    G: nx.Graph,
    base_ings: List[str],
    goal: str = "default",
    top_k: int = 10,
    min_cooc: int = 5,
) -> List[str]:
    """
    Suggest ingredients that pair well with base_ings.

    goal:
      - "default": pure co-occurrence
      - "high_rating": prefer neighbors from highly-rated recipes
      - "healthy": prefer neighbors from lower-calorie contexts
    """
    base_ings_norm = [normalize_ing(b) for b in base_ings]
    scores: Dict[str, float] = {}

    for ing in base_ings_norm:
        if ing not in G:
            continue
        for neigh, data in G[ing].items():
            cooc = data.get("cooc", 0)
            if cooc < min_cooc:
                continue
            base_score = cooc

            node = G.nodes[neigh]
            rating = node.get("avg_rating", 0.0)
            cal = node.get("avg_calories", 0.0)

            if goal == "high_rating":
                # boost by rating (0-5)
                score = base_score * (1.0 + rating / 5.0)
            elif goal == "healthy":
                # favor lower-calorie ingredients
                score = base_score * (1.0 + 1.0 / (1.0 + cal / 200.0))
            else:
                score = base_score

            scores[neigh] = scores.get(neigh, 0.0) + score

    # Remove base ingredients from results
    for b in base_ings_norm:
        scores.pop(b, None)

    ranked = sorted(scores.items(), key=lambda x: -x[1])
    return [ing for ing, _ in ranked[:top_k]]


def cli():
    print("=== FlavorGraphAI v1 ===")
    print("Building the ingredient graph (this may take a few minutes)...")
    G = build_graph(max_recipes=50000)

    while True:
        raw = input(
            "\nEnter base ingredients (comma-separated, or 'q' to quit): "
        ).strip()
        if raw.lower() in {"q", "quit", "exit"}:
            break

        base_ings = [x.strip() for x in raw.split(",") if x.strip()]
        if not base_ings:
            print("Please enter at least one ingredient.")
            continue

        goal = input("Goal [default/high_rating/healthy]: ").strip().lower()
        if goal not in {"default", "high_rating", "healthy"}:
            goal = "default"

        suggestions = suggest_neighbors_scored(
            G,
            base_ings,
            goal=goal,
            top_k=10,
            min_cooc=5,
        )

        if not suggestions:
            print("No suggestions found. Try more common ingredients or a different goal.")
        else:
            print(f"\nSuggested ingredients for {base_ings} (goal = {goal}):")
            print(", ".join(suggestions))


if __name__ == "__main__":
    cli()

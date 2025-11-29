from __future__ import annotations

from typing import List, Dict, Tuple, Any

from datasets import load_dataset
from flavorgraph_ai import normalize_ing


def _parse_list_string(raw: str | None) -> list[str]:
    """
    Parse R-style c(\"a\", \"b\") strings, plain quoted strings,
    or comma-separated lists into a list of strings.

    Examples:
      character(0)                      -> []
      "https://..."                     -> ["https://..."]
      c("url1", "url2")                 -> ["url1", "url2"]
    """
    if not raw:
        return []

    s = raw.strip()

    # Explicit "no value" marker from the dataset
    if s == "character(0)" or s == '"character(0)"':
        return []

    # Strip leading/trailing c( )
    if s.startswith("c(") and s.endswith(")"):
        s = s[2:-1].strip()

    if not s:
        return []

    parts: list[str] = []
    for part in s.split(","):
        part = part.strip()
        # Remove surrounding quotes
        if part.startswith('"') or part.startswith("'"):
            part = part[1:]
        if part.endswith('"') or part.endswith("'"):
            part = part[:-1]
        part = part.strip()
        if part:
            parts.append(part)
    return parts



def _first_image_url(raw: str | None) -> str | None:
    """
    Return the first valid image URL from the Images field.

    Handles:
      - character(0)        -> None
      - "https://..."       -> that URL
      - c("url1","url2")    -> the first URL
    """
    if not raw:
        return None

    s = raw.strip()

    # Explicit "no image" marker
    if s == "character(0)" or s == '"character(0)"':
        return None

    # Fast path: if there's no 'http' at all, don't bother
    if "http" not in s:
        return None

    urls = _parse_list_string(raw)

    # Return first thing that looks like a real URL
    for u in urls:
        if u.startswith("http://") or u.startswith("https://"):
            return u

    return None



def load_recipes_for_subgraph(
    center_ing: str,
    subgraph_nodes: list[str],
    max_recipes: int,
) -> tuple[list[dict[str, Any]], dict[str, list[int]]]:
    """
    Load recipes (up to max_recipes) from the HF dataset that contain
    the center ingredient, and build:
      - recipes: list of recipe dicts
      - ing_to_recipes: mapping ingredient -> list of *local* recipe indices

    Only ingredients that are in subgraph_nodes are tracked.
    """
    ds = load_dataset("AkashPS11/recipes_data_food.com", split="train")

    node_set = set(subgraph_nodes)
    recipes: list[dict[str, Any]] = []
    ing_to_recipes: dict[str, list[int]] = {n: [] for n in node_set}

    for idx, rec in enumerate(ds):
        if idx >= max_recipes:
            break

        parts_raw = rec.get("RecipeIngredientParts") or ""
        parts = _parse_list_string(parts_raw)
        norm_ings = [normalize_ing(p) for p in parts]

        # Only keep recipes that include the center ingredient
        if center_ing not in norm_ings:
            continue

        recipe_index = len(recipes)

        recipes.append(
            {
                "idx": idx,
                "name": rec.get("Name") or "",
                "ingredients": parts,
                "image": _first_image_url(rec.get("Images")),
                "rating": float(rec.get("AggregatedRating") or 0.0),
                "calories": float(rec.get("Calories") or 0.0),
            }
        )

        # Link every ingredient in this recipe that appears in our subgraph
        for ing in norm_ings:
            if ing in node_set:
                ing_to_recipes[ing].append(recipe_index)

    return recipes, ing_to_recipes

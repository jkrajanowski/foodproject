import matplotlib.pyplot as plt
import networkx as nx

from flavorgraph_ai import build_graph, normalize_ing


def visualize_neighborhood(
    center_ing: str,
    max_recipes: int = 10000,
    max_neighbors: int = 25,
):
    """
    Build the ingredient graph (on a subset of recipes) and visualize
    the local neighborhood of one ingredient (center_ing).
    """
    center_ing = normalize_ing(center_ing)

    print(f"Building graph from first {max_recipes} recipes...")
    G = build_graph(max_recipes=max_recipes)

    if center_ing not in G:
        print(f"Ingredient '{center_ing}' not found in graph.")
        return

    neighbors = list(G.neighbors(center_ing))
    if not neighbors:
        print(f"No neighbors found for '{center_ing}'.")
        return

    # Limit number of neighbors for readability
    neighbors = neighbors[:max_neighbors]

    sub_nodes = [center_ing] + neighbors
    H = G.subgraph(sub_nodes).copy()

    print(
        f"Visualizing '{center_ing}' with {len(neighbors)} neighbors "
        f"({H.number_of_edges()} edges)..."
    )

    # Layout for nodes
    pos = nx.spring_layout(H, k=0.6, iterations=50, seed=42)

    # Node sizes: make the center ingredient bigger
    node_sizes = [
        900 if n == center_ing else 300 for n in H.nodes()
    ]

    # Node colors: center is one color, neighbors another
    node_colors = [
        "orange" if n == center_ing else "skyblue" for n in H.nodes()
    ]

    plt.figure(figsize=(10, 8))
    nx.draw_networkx(
        H,
        pos,
        with_labels=True,
        node_size=node_sizes,
        node_color=node_colors,
        font_size=8,
        edge_color="gray",
    )
    plt.title(f"Flavor neighborhood of '{center_ing}'")
    plt.axis("off")
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    # Change this to visualize different ingredients
    ingredient = input("Ingredient to visualize (e.g. chicken, chocolate): ")
    if ingredient.strip():
        visualize_neighborhood(ingredient.strip())
    else:
        print("No ingredient provided.")

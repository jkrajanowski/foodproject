from pathlib import Path

import networkx as nx
import plotly.graph_objects as go

from flavorgraph_ai import build_graph, normalize_ing


def build_neighborhood_subgraph(
    G: nx.Graph,
    center_ing: str,
    max_neighbors: int = 40,
) -> nx.Graph:
    center_ing = normalize_ing(center_ing)
    if center_ing not in G:
        raise ValueError(f"Ingredient '{center_ing}' not found in graph.")
    neighbors = list(G.neighbors(center_ing))
    if not neighbors:
        raise ValueError(f"No neighbors found for '{center_ing}'.")
    neighbors = neighbors[:max_neighbors]
    sub_nodes = [center_ing] + neighbors
    return G.subgraph(sub_nodes).copy()


def popularity_color(count: int, max_count: int) -> str:
    """
    Neon-ish color mapping for popularity (count):
      low  -> blue
      mid  -> purple
      high -> pink
    """
    if max_count <= 0:
        return "#7f8c8d"
    ratio = count / max_count
    if ratio < 0.33:
        return "#3498db"   # blue
    elif ratio < 0.66:
        return "#9b59b6"   # purple
    else:
        return "#e91e63"   # pink


def visualize_3d(
    center_ing: str,
    max_recipes: int = 100000,
    max_neighbors: int = 40,
    output_html: str | None = None,
):
    center_ing = normalize_ing(center_ing)
    print(f"Building graph from first {max_recipes} recipes...")
    G = build_graph(max_recipes=max_recipes)

    print(f"Extracting neighborhood for '{center_ing}'...")
    H = build_neighborhood_subgraph(G, center_ing, max_neighbors=max_neighbors)
    print(f"Subgraph: {H.number_of_nodes()} nodes, {H.number_of_edges()} edges.")

    # 3D layout
    print("Computing 3D layout...")
    pos_3d = nx.spring_layout(H, dim=3, seed=42)

    # Popularity stats for colors & sizes
    max_count = 1
    for node in H.nodes():
        c = G.nodes[node].get("count", 0)
        if c > max_count:
            max_count = c

    # Node coordinates, sizes, colors, labels
    node_x = []
    node_y = []
    node_z = []
    node_text = []
    node_color = []
    node_size = []

    for node, (x, y, z) in pos_3d.items():
        data = G.nodes[node]
        count = data.get("count", 0)
        avg_rating = data.get("avg_rating", 0.0)
        avg_cal = data.get("avg_calories", 0.0)

        node_x.append(x)
        node_y.append(y)
        node_z.append(z)

        # Hover text
        node_text.append(
            f"{node}<br>"
            f"Popularity: {count} recipes<br>"
            f"Avg rating: {avg_rating:.2f}<br>"
            f"Avg calories: {avg_cal:.1f}"
        )

        color = popularity_color(count, max_count)
        node_color.append(color)

        ratio = count / max_count if max_count > 0 else 0
        base_size = 6 + 10 * ratio  # 6–16
        size = base_size + 4 if node == center_ing else base_size
        node_size.append(size)

    # Edge coordinates
    edge_x = []
    edge_y = []
    edge_z = []

    for src, dst, edata in H.edges(data=True):
        cooc = edata.get("cooc", 1)
        if cooc < 5:
            continue  # skip weak edges to make it less dense

        x0, y0, z0 = pos_3d[src]
        x1, y1, z1 = pos_3d[dst]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]
        edge_z += [z0, z1, None]

    edge_trace = go.Scatter3d(
        x=edge_x,
        y=edge_y,
        z=edge_z,
        mode="lines",
        line=dict(color="#5c6c80", width=2),
        hoverinfo="none",
    )

    node_trace = go.Scatter3d(
        x=node_x,
        y=node_y,
        z=node_z,
        mode="markers+text",
        text=[n for n in H.nodes()],
        textposition="top center",
        marker=dict(
            size=node_size,
            color=node_color,
            line=dict(color="#111111", width=0.5),
        ),
        hoverinfo="text",
        textfont=dict(color="#ffffff"),
    )

    if output_html is None:
        safe_name = center_ing.replace(" ", "_")
        output_html = f"flavorgraph_{safe_name}_3d.html"

    output_path = Path(output_html).resolve()
    print(f"Saving 3D graph to: {output_path}")

    fig = go.Figure(data=[edge_trace, node_trace])
    fig.update_layout(
        title=f"3D Flavor Neighborhood of '{center_ing}'",
        showlegend=False,
        scene=dict(
            xaxis=dict(showbackground=False, showticklabels=False, visible=False),
            yaxis=dict(showbackground=False, showticklabels=False, visible=False),
            zaxis=dict(showbackground=False, showticklabels=False, visible=False),
            bgcolor="#050816",
        ),
        paper_bgcolor="#050816",
        margin=dict(l=0, r=0, t=40, b=0),
    )

    # NOTE: Plotly doesn't auto-rotate by default; you can rotate with the mouse.
    # Auto-rotation would require custom JS; this keeps it simple & portable.

    fig.write_html(str(output_path), auto_open=True)
    print("Done. The graph should now open in your browser.")


if __name__ == "__main__":
    ing = input("Ingredient to visualize in 3D (e.g. chicken, chocolate): ").strip()
    if not ing:
        print("No ingredient provided, exiting.")
    else:
        try:
            visualize_3d(ing)
        except ValueError as e:
            print(f"Error: {e}")

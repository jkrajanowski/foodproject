from __future__ import annotations

from pathlib import Path
import json
from typing import Any


def inject_recipe_data(
    output_path: Path,
    recipes: list[dict[str, Any]],
    ing_to_recipes: dict[str, list[int]],
) -> None:
    """Inject recipe data as JS variables into the HTML."""
    html = output_path.read_text(encoding="utf-8")

    data_script = """
<script type="text/javascript">
  window.fgRecipes = %s;
  window.fgIngToRecipes = %s;
</script>
""" % (json.dumps(recipes), json.dumps(ing_to_recipes))

    marker = "</body>"
    idx = html.rfind(marker)
    if idx == -1:
        new_html = html + data_script
    else:
        new_html = html[:idx] + data_script + html[idx:]

    output_path.write_text(new_html, encoding="utf-8")


def inject_controls(output_path: Path) -> None:
    """Inject UI controls (modes, search, slider, info, recipes) into the Pyvis HTML."""
    html = output_path.read_text(encoding="utf-8")

    controls_html = '''
<!-- FlavorGraphAI controls (left) -->
<div id="fg-controls" 
     style="
       position: absolute;
       top: 10px;
       left: 10px;
       z-index: 9999;
       background: rgba(5, 8, 22, 0.9);
       padding: 10px 12px;
       border-radius: 8px;
       border: 1px solid #444;
       color: #ecf0f1;
       font-family: Arial, sans-serif;
       font-size: 13px;
     ">
  <div style="margin-bottom: 8px; font-weight: bold; font-size: 14px;">
    FlavorGraphAI Controls
  </div>

  <!-- Color mode buttons -->
  <div style="margin-bottom: 8px;">
    <span style="display:block; margin-bottom:4px;">Color mode:</span>
    <button onclick="fgSetColorMode('pop')" 
            style="padding:3px 6px; border-radius:4px; border:none; background:#3498db; color:white; margin-right:4px;">
      Popularity
    </button>
    <button onclick="fgSetColorMode('cal')" 
            style="padding:3px 6px; border-radius:4px; border:none; background:#2ecc71; color:white; margin-right:4px;">
      Calories
    </button>
    <button onclick="fgSetColorMode('rat')" 
            style="padding:3px 6px; border-radius:4px; border:none; background:#f1c40f; color:black; margin-right:4px;">
      Rating
    </button>
    <button onclick="fgSetColorMode('clu')" 
            style="padding:3px 6px; border-radius:4px; border:none; background:#e67e22; color:white;">
      Clusters
    </button>
  </div>

  <!-- Search -->
  <div style="margin-bottom: 8px;">
    <label for="fg-search" style="display:block; margin-bottom:4px;">
      Search ingredient:
    </label>
    <input id="fg-search" type="text" 
           placeholder="e.g. chicken"
           style="width: 160px; padding: 3px 5px; border-radius: 4px; border: 1px solid #555;" />
    <button onclick="fgSearchNode()" 
            style="margin-left: 4px; padding: 3px 8px; border-radius: 4px; border:none; background:#9b59b6; color:white;">
      Go
    </button>
  </div>

  <!-- Edge strength slider -->
  <div style="margin-bottom: 8px;">
    <label for="fg-min-cooc" style="display:block; margin-bottom:4px;">
      Min co-occurrence: <span id="fg-min-cooc-value">0</span>
    </label>
    <input id="fg-min-cooc" type="range" min="0" max="20" value="3"
           style="width: 200px;" oninput="fgUpdateMinCooc()" />
  </div>

  <!-- Node info panel -->
  <div id="fg-node-info" 
       style="margin-top: 10px; padding-top: 8px; border-top: 1px solid #555; font-size: 12px;">
    <em>Click a node to see its stats.</em>
  </div>

  <div style="margin-top: 6px; font-size: 11px; opacity: 0.8;">
    Tip: Ctrl+click multiple ingredients to filter recipes.
  </div>
</div>

<!-- Recipes panel (right) -->
<div id="fg-recipe-panel"
     style="
       position: absolute;
       top: 10px;
       right: 10px;
       z-index: 9999;
       width: 340px;
       max-height: 90vh;
       overflow-y: auto;
       background: rgba(5, 8, 22, 0.9);
       padding: 10px 12px;
       border-radius: 8px;
       border: 1px solid #444;
       color: #ecf0f1;
       font-family: Arial, sans-serif;
       font-size: 13px;
     ">
  <div style="margin-bottom: 8px; font-weight: bold; font-size: 14px;">
    Matching recipes
  </div>
  <div id="fg-recipe-list">
    <em>Select one or more ingredients to see recipes.</em>
  </div>
</div>

<script type="text/javascript">
  function fgSetColorMode(mode) {
    if (typeof nodes === 'undefined') {
      console.log('nodes not ready');
      return;
    }
    var allNodes = nodes.get();
    var updates = [];
    for (var i = 0; i < allNodes.length; i++) {
      var n = allNodes[i];

      if (mode === 'pop') {
        if (n.color_pop) {
          n.color = n.color_pop;
        }
        if (n.size_pop) {
          n.size = n.size_pop;
        }
      } else if (mode === 'cal') {
        if (n.color_cal) {
          n.color = n.color_cal;
        }
        if (n.size_cal) {
          n.size = n.size_cal;
        }
      } else if (mode === 'rat') {
        if (n.color_rat) {
          n.color = n.color_rat;
        }
        if (n.size_rat) {
          n.size = n.size_rat;
        }
      } else if (mode === 'clu') {
        if (n.color_clu) {
          n.color = n.color_clu;
        }
        if (n.size_clu) {
          n.size = n.size_clu;
        }
      }

      updates.push(n);
    }
    if (updates.length > 0) {
      nodes.update(updates);
    }
  }

  function fgUpdateNodeInfoById(nodeId) {
    var panel = document.getElementById('fg-node-info');
    if (!panel) return;

    if (!nodeId) {
      panel.innerHTML = "<em>Click a node to see its stats.</em>";
      return;
    }
    var n = nodes.get(nodeId);
    if (!n) {
      panel.innerHTML = "<em>No data for this node.</em>";
      return;
    }
    if (n.info_html) {
      panel.innerHTML = n.info_html;
    } else if (n.title) {
      panel.innerHTML = n.title;
    } else {
      panel.innerHTML = "<b>" + (n.label || nodeId) + "</b>";
    }
  }

  function fgSearchNode() {
    if (typeof nodes === 'undefined' || typeof network === 'undefined') {
      alert('Graph not ready');
      return;
    }
    var queryInput = document.getElementById('fg-search');
    if (!queryInput) return;
    var query = queryInput.value.toLowerCase().trim();
    if (!query) return;

    var allNodes = nodes.get();
    var found = null;
    for (var i = 0; i < allNodes.length; i++) {
      var label = (allNodes[i].label || '').toLowerCase();
      if (label === query) {
        found = allNodes[i];
        break;
      }
    }
    if (!found) {
      alert('No node found: ' + query);
      return;
    }

    network.selectNodes([found.id]);
    network.focus(found.id, {
      scale: 1.4,
      animation: { duration: 800, easingFunction: 'easeInOutQuad' }
    });
  }

  function fgUpdateMinCooc() {
    if (typeof edges === 'undefined') return;

    var slider = document.getElementById('fg-min-cooc');
    var labelSpan = document.getElementById('fg-min-cooc-value');
    if (!slider || !labelSpan) return;

    var threshold = parseInt(slider.value);
    labelSpan.innerText = threshold;

    var allEdges = edges.get();
    var updates = [];
    for (var i = 0; i < allEdges.length; i++) {
      var e = allEdges[i];
      var cooc = e.value || 0;
      var shouldHide = cooc < threshold;
      if (!!e.hidden !== shouldHide) {
        e.hidden = shouldHide;
        updates.push(e);
      }
    }
    if (updates.length > 0) {
      edges.update(updates);
    }
  }

  function fgUpdateRecipePanel(selectedIngs) {
    var container = document.getElementById('fg-recipe-list');
    if (!container) return;

    if (!selectedIngs || selectedIngs.length === 0) {
      container.innerHTML = "<em>Select one or more ingredients to see recipes.</em>";
      return;
    }

    if (typeof window.fgIngToRecipes === 'undefined' || typeof window.fgRecipes === 'undefined') {
      container.innerHTML = "<em>Recipe data not available.</em>";
      return;
    }

    // Get intersection of recipe indices across all selected ingredients
    var first = selectedIngs[0];
    var baseList = window.fgIngToRecipes[first] || [];
    if (baseList.length === 0) {
      container.innerHTML = "<em>No recipes found for this combination.</em>";
      return;
    }

    var otherSets = [];
    for (var i = 1; i < selectedIngs.length; i++) {
      var ing = selectedIngs[i];
      var ids = window.fgIngToRecipes[ing] || [];
      var set = {};
      for (var j = 0; j < ids.length; j++) {
        set[ids[j]] = true;
      }
      otherSets.push(set);
    }

    var matched = [];
    for (var i = 0; i < baseList.length; i++) {
      var ridx = baseList[i];
      var ok = true;
      for (var s = 0; s < otherSets.length && ok; s++) {
        if (!otherSets[s][ridx]) {
          ok = false;
        }
      }
      if (ok) {
        matched.push(ridx);
      }
    }

    if (matched.length === 0) {
      container.innerHTML = "<em>No recipes found for this combination.</em>";
      return;
    }

    // Render up to 30 recipes
    var html = "";
    var limit = Math.min(30, matched.length);
    for (var k = 0; k < limit; k++) {
      var r = window.fgRecipes[matched[k]];
      if (!r) continue;

      var imgHtml = "";
      if (r.image) {
        imgHtml = '<div style="margin-bottom:6px;"><img src="' + r.image + '" style="max-width:100%; border-radius:6px;" /></div>';
      }

      var ingsText = (r.ingredients || []).join(", ");

      html += '<div style="margin-bottom:10px; padding-bottom:8px; border-bottom:1px solid #555;">'
           +  '<div style="font-weight:bold; margin-bottom:4px;">' + (r.name || "Unnamed recipe") + '</div>'
           +  imgHtml
           +  '<div style="font-size:12px; margin-bottom:4px;"><b>Ingredients:</b> ' + ingsText + '</div>'
           +  '<div style="font-size:11px; opacity:0.8;">Rating: ' + (r.rating || 0).toFixed(2)
           +  ' | Calories: ' + (r.calories || 0).toFixed(1) + '</div>'
           +  '</div>';
    }

    if (matched.length > limit) {
      html += '<div style="font-size:11px; opacity:0.7;">Showing '
           + limit + ' of ' + matched.length + ' recipes.</div>';
    }

    container.innerHTML = html;
  }

  document.addEventListener('DOMContentLoaded', function() {
    var slider = document.getElementById('fg-min-cooc');
    if (slider) {
      fgUpdateMinCooc();
    }

    fgUpdateNodeInfoById(null);
    fgUpdateRecipePanel([]);

    // Attach click handler to update info panel and recipes
    if (typeof network !== 'undefined') {
      network.on("click", function(params) {
        var selected = network.getSelectedNodes();  // supports multiselect
        if (selected && selected.length > 0) {
          // For node info, just show first selected
          fgUpdateNodeInfoById(selected[0]);
        } else {
          fgUpdateNodeInfoById(null);
        }
        fgUpdateRecipePanel(selected);
      });
    }
  });
</script>
'''

    marker = "</body>"
    idx = html.rfind(marker)
    if idx == -1:
        new_html = html + controls_html
    else:
        new_html = html[:idx] + controls_html + html[idx:]

    output_path.write_text(new_html, encoding="utf-8")

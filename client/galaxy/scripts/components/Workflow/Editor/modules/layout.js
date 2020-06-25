import $ from "jquery";

export function autoLayout(workflow) {
    workflow.hasChanges = true;
    // Prepare predecessor / successor tracking
    const n_pred = {};
    const successors = {};
    // First pass to initialize arrays even for nodes with no connections
    Object.keys(workflow.nodes).forEach((id) => {
        if (n_pred[id] === undefined) {
            n_pred[id] = 0;
        }
        if (successors[id] === undefined) {
            successors[id] = [];
        }
    });
    // Second pass to count predecessors and successors
    Object.values(workflow.nodes).forEach((node) => {
        Object.values(node.inputTerminals).forEach((t) => {
            t.connectors.forEach((c) => {
                // A connection exists from `other` to `node`
                const other = c.outputHandle.node;
                // node gains a predecessor
                n_pred[node.id] += 1;
                // other gains a successor
                successors[other.id].push(node.id);
            });
        });
    });
    // Assemble order, tracking levels
    const node_ids_by_level = [];
    for (;;) {
        // Everything without a predecessor
        const level_parents = [];
        for (const pred_k in n_pred) {
            if (n_pred[pred_k] === 0) {
                level_parents.push(pred_k);
            }
        }
        if (level_parents.length === 0) {
            break;
        }
        node_ids_by_level.push(level_parents);
        // Remove the parents from this level, and decrement the number
        // of predecessors for each successor
        for (const k in level_parents) {
            const v = level_parents[k];
            delete n_pred[v];
            for (const sk in successors[v]) {
                n_pred[successors[v][sk]] -= 1;
            }
        }
    }
    if (n_pred.length) {
        // ERROR: CYCLE! Currently we do nothing
        return;
    }
    // Layout each level
    const all_nodes = workflow.nodes;
    const h_pad = 80;
    const v_pad = 30;
    let left = h_pad;
    node_ids_by_level.forEach((ids) => {
        // We keep nodes in the same order in a level to give the user
        // some control over ordering
        ids.sort(
            (a, b) =>
                all_nodes[a].element.getBoundingClientRect().top - all_nodes[b].element.getBoundingClientRect().top
        );
        // Position each node
        let max_width = 0;
        let top = v_pad;
        ids.forEach((id) => {
            const node = all_nodes[id];
            const element = $(node.element);
            $(element).css({ top: top, left: left });
            max_width = Math.max(max_width, $(element).width());
            top += $(element).height() + v_pad;
        });
        left += max_width + h_pad;
    });
    // Need to redraw all connectors
    Object.values(all_nodes).forEach((node) => {
        node.onRedraw();
    });
}

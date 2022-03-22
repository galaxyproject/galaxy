import $ from "jquery";
import ELK from "elkjs/lib/elk.bundled.js";
const elk = new ELK();

export function autoLayout(workflow) {
    workflow.hasChanges = true;

    // Convert this to ELK compat.
    var newgraph = {
        id: "",
        layoutOptions: {
            "elk.algorithm": "layered",
            "crossingMinimization.semiInteractive": true,
            "nodePlacement.strategy": "NETWORK_SIMPLEX",
        },
        children: [],
        edges: [],
    };

    newgraph.children = Object.values(workflow.nodes).map((node) => {
        var inputs = Object.keys(node.inputTerminals).map((t, idx) => {
            return {
                id: `${node._uid}/in/${t}`,
                properties: {
                    "port.side": "WEST",
                    "port.index": idx,
                },
            };
        });

        var outputs = Object.keys(node.outputTerminals).map((t, idx) => {
            return {
                id: `${node._uid}/out/${t}`,
                properties: {
                    "port.side": "EAST",
                    "port.index": idx,
                },
            };
        });

        return {
            id: node._uid,
            height: $(node.element).height() + 20,
            width: $(node.element).width() + 60,
            ports: inputs.concat(outputs),
        };
    });

    Object.values(workflow.nodes).forEach((node) => {
        Object.values(node.inputTerminals).forEach((t) => {
            t.connectors.forEach((c) => {
                newgraph.edges.push({
                    id: `e_${node._uid}_${c.outputHandle.node._uid}`,
                    sources: [`${c.outputHandle.node._uid}/out/${c.outputHandle.name}`],
                    targets: [`${c.inputHandle.node._uid}/in/${c.inputHandle.name}`],
                });
            });
        });
    });

    elk.layout(newgraph)
        .then((x) => {
            // Reapply positions to galaxy graph from our relayed out graph.
            x.children.forEach((q) => {
                var node = Object.values(workflow.nodes).filter((x) => {
                    return x._uid === q.id;
                })[0];
                const element = $(node.element);
                $(element).css({ top: q.y, left: q.x });
            });

            Object.values(workflow.nodes).forEach((node) => {
                node.onRedraw();
            });
        })
        .catch(console.error);
}

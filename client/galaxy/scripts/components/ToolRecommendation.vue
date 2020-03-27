<template>
    <div id="tool-recommendation" class="tool-recommendation-view">
        <div v-if="!deprecated" class="infomessagelarge">
            <h4>Tool recommendation</h4>
            You have used {{ getToolId }} tool. For further analysis, you could try using the following/recommended
            tools. The recommended tools are shown in the decreasing order of their scores predicted using machine
            learning analysis on workflows. A tool with a higher score (closer to 100%) may fit better as the following
            tool than a tool with a lower score. Please click on one of the following/recommended tools to open its
            definition.
        </div>
        <div v-else class="warningmessagelarge">You have used {{ getToolId }} tool. {{ deprecatedMessage }}</div>
    </div>
</template>

<script>
import * as d3 from "d3";
import { getAppRoot } from "onload/loadConfig";
import axios from "axios";

export default {
    props: {
        toolId: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            deprecated: null,
            deprecatedMessage: "",
        };
    },
    created() {
        this.loadRecommendations();
    },
    computed: {
        getToolId() {
            let toolId = this.toolId || "";
            if (toolId.indexOf("/") > 0) {
                const toolIdSlash = toolId.split("/");
                toolId = toolIdSlash[toolIdSlash.length - 2];
            }
            return toolId;
        },
    },
    methods: {
        loadRecommendations() {
            const toolId = this.getToolId;
            const url = `${getAppRoot()}api/workflows/get_tool_predictions`;
            axios
                .post(url, {
                    tool_sequence: toolId,
                })
                .then((response) => {
                    axios.get(`${getAppRoot()}api/datatypes/mapping`).then((responseMapping) => {
                        const predData = response.data.predicted_data;
                        const datatypesMapping = responseMapping.data;
                        const extToType = datatypesMapping.ext_to_class_name;
                        const typeToType = datatypesMapping.class_to_classes;
                        this.deprecated = predData.is_deprecated;

                        if (response.data !== null && predData.children.length > 0) {
                            const filteredData = {};
                            const compatibleTools = {};
                            const filteredChildren = [];
                            const outputDatatypes = predData.o_extensions;
                            const children = predData.children;
                            for (const nameObj of children.entries()) {
                                const inputDatatypes = nameObj[1].i_extensions;
                                for (const out_t of outputDatatypes.entries()) {
                                    for (const in_t of inputDatatypes.entries()) {
                                        const child = extToType[out_t[1]];
                                        const parent = extToType[in_t[1]];
                                        if (
                                            (typeToType[child] && parent in typeToType[child]) === true ||
                                            out_t[1] === "input" ||
                                            out_t[1] === "_sniff_" ||
                                            out_t[1] === "input_collection"
                                        ) {
                                            compatibleTools[nameObj[1].tool_id] = nameObj[1].name;
                                            break;
                                        }
                                    }
                                }
                            }
                            for (const id in compatibleTools) {
                                for (const nameObj of children.entries()) {
                                    if (nameObj[1].tool_id === id) {
                                        filteredChildren.push(nameObj[1]);
                                        break;
                                    }
                                }
                            }
                            filteredData.o_extensions = predData.o_extensions;
                            filteredData.name = predData.name;
                            filteredData.children = filteredChildren;
                            if (filteredChildren.length > 0 && this.deprecated === false) {
                                this.renderD3Tree(filteredData);
                            } else if (this.deprecated === true) {
                                this.deprecatedMessage = predData.message;
                            }
                        }
                    });
                });
        },
        renderD3Tree(predictedTools) {
            const duration = 750;
            const svg = d3.select("#tool-recommendation").append("svg").attr("class", "tree-size").append("g");
            let i = 0;
            let root = null;
            let x = 0;
            let y = 0;
            let translateX = 0;

            const gElem = svg[0][0];
            const svgElem = gElem.parentNode;
            const clientH = svgElem.clientHeight;
            const clientW = svgElem.clientWidth;
            y = parseInt(clientH * 0.9);
            x = parseInt(clientW * 0.6);
            translateX = parseInt(clientW * 0.15);

            svgElem.setAttribute("viewBox", "0 0 " + x + " " + clientH);
            svgElem.setAttribute("preserveAspectRatio", "xMinYMin");
            gElem.setAttribute("transform", "translate(" + translateX + ", 5)");

            const tree = d3.layout.tree().size([y, x]);

            const diagonal = d3.svg.diagonal().projection((d) => {
                return [d.y, d.x];
            });
            const update = (source) => {
                // Compute the new tree layout.
                const nodes = tree.nodes(root).reverse();
                const links = tree.links(nodes);
                // Normalize for fixed-depth.
                nodes.forEach((d) => {
                    d.y = d.depth * 180;
                });
                // Update the nodes…
                const node = svg.selectAll("g.node").data(nodes, (d) => {
                    return d.id || (d.id = ++i);
                });
                // Enter any new nodes at the parent's previous position.
                const nodeEnter = node
                    .enter()
                    .append("g")
                    .attr("class", "node")
                    .attr("transform", (d) => {
                        return "translate(" + source.y0 + "," + source.x0 + ")";
                    })
                    .on("click", click);
                nodeEnter.append("circle").attr("r", 1e-6);
                nodeEnter
                    .append("text")
                    .attr("x", (d) => {
                        return d.children || d._children ? -10 : 10;
                    })
                    .attr("dy", ".35em")
                    .attr("text-anchor", (d) => {
                        return d.children || d._children ? "end" : "start";
                    })
                    .text((d) => {
                        return d.name;
                    })
                    .attr("class", "node-enter");
                nodeEnter.append("title").text((d) => {
                    return d.children || d._children ? "Click to collapse" : "Click to open tool definition";
                });
                // Transition nodes to their new position.
                const nodeUpdate = node
                    .transition()
                    .duration(duration)
                    .attr("transform", (d) => {
                        return "translate(" + d.y + "," + d.x + ")";
                    });
                nodeUpdate.select("circle").attr("r", 4.5);
                nodeUpdate.select("text").attr("class", "node-update");
                // Transition exiting nodes to the parent's new position.
                const nodeExit = node
                    .exit()
                    .transition()
                    .duration(duration)
                    .attr("transform", (d) => {
                        return "translate(" + source.y + "," + source.x + ")";
                    })
                    .remove();
                nodeExit.select("circle").attr("r", 1e-6);
                nodeExit.select("text").attr("class", "node-enter");
                // Update the links
                const link = svg.selectAll("path.link").data(links, (d) => {
                    return d.target.id;
                });
                // Enter any new links at the parent's previous position.
                link.enter()
                    .insert("path", "g")
                    .attr("class", "link")
                    .attr("d", (d) => {
                        const o = { x: source.x0, y: source.y0 };
                        return diagonal({ source: o, target: o });
                    });
                // Transition links to their new position.
                link.transition().duration(duration).attr("d", diagonal);
                // Transition exiting nodes to the parent's new position.
                link.exit()
                    .transition()
                    .duration(duration)
                    .attr("d", (d) => {
                        const o = { x: source.x, y: source.y };
                        return diagonal({ source: o, target: o });
                    })
                    .remove();
                // Stash the old positions for transition.
                nodes.forEach((d) => {
                    d.x0 = d.x;
                    d.y0 = d.y;
                });
            };
            // Toggle children on click.
            const click = (d) => {
                if (d.children) {
                    d._children = d.children;
                    d.children = null;
                } else {
                    d.children = d._children;
                    d._children = null;
                }
                update(d);
                const tId = d.tool_id;
                if (tId !== undefined && tId !== "undefined" && tId !== null && tId !== "") {
                    document.location.href = `${getAppRoot()}tool_runner?tool_id=${tId}`;
                }
            };
            const collapse = (d) => {
                if (d.children) {
                    d._children = d.children;
                    d._children.forEach(collapse);
                    d.children = null;
                }
            };
            root = predictedTools;
            root.x0 = y / 2;
            root.y0 = 0;
            root.children.forEach(collapse);
            update(root);
        },
    },
};
</script>

<template>
    <div aria-labelledby="tool-recommendation-heading">
        <div v-if="!deprecated && showMessage" class="infomessagelarge">
            <h2 id="tool-recommendation-heading" class="h-sm">Tool recommendation</h2>
            You have used {{ getToolId }} tool. For further analysis, you could try using the following/recommended
            tools. The recommended tools are shown in the decreasing order of their scores predicted using machine
            learning analysis on workflows. Therefore, tools at the top may be more useful than the ones at the bottom.
            Please click on one of the following/recommended tools to open its definition.
        </div>
        <div v-else-if="deprecated" class="warningmessagelarge">
            <h2 id="tool-recommendation-heading" class="h-sm">Tool deprecated</h2>
            You have used {{ getToolId }} tool. {{ deprecatedMessage }}
        </div>
        <div id="tool-recommendation" class="ui-tool-recommendation"></div>
    </div>
</template>

<script>
import * as d3 from "d3";
import { getAppRoot } from "onload/loadConfig";
import { getDatatypesMapper } from "components/Datatypes";
import { getToolPredictions } from "components/Workflow/Editor/modules/services";
import { getCompatibleRecommendations } from "components/Workflow/Editor/modules/utilities";

export default {
    props: {
        toolId: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            deprecated: false,
            deprecatedMessage: "",
            showMessage: false,
        };
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
    created() {
        this.loadRecommendations();
    },
    methods: {
        loadRecommendations() {
            const toolId = this.getToolId;
            const requestData = {
                tool_sequence: toolId,
            };
            getToolPredictions(requestData).then((responsePred) => {
                getDatatypesMapper(false).then((datatypesMapper) => {
                    const predData = responsePred.predicted_data;
                    this.deprecated = predData.is_deprecated;
                    this.deprecatedMessage = predData.message;
                    if (responsePred !== null && predData.children.length > 0) {
                        const filteredData = {};
                        const outputDatatypes = predData.o_extensions;
                        const children = predData.children;
                        const compatibleTools = getCompatibleRecommendations(
                            children,
                            outputDatatypes,
                            datatypesMapper
                        );
                        if (compatibleTools.length > 0 && this.deprecated === false) {
                            this.showMessage = true;
                            filteredData.o_extensions = predData.o_extensions;
                            filteredData.name = predData.name;
                            filteredData.children = compatibleTools;
                            this.renderD3Tree(filteredData);
                        }
                    }
                });
            });
        },
        renderD3Tree(predictedTools) {
            let i = 0;
            let root = null;
            const duration = 750;
            const maxTextLength = 20;
            const svg = d3.select("#tool-recommendation").append("svg").attr("class", "tree-size").append("g");
            const gElem = svg[0][0];
            const svgElem = gElem.parentNode;
            const clientH = svgElem.clientHeight;
            const clientW = svgElem.clientWidth;
            const translateX = parseInt(clientW * 0.15);

            svgElem.setAttribute("viewBox", -translateX + " 0 " + 0.5 * clientW + " " + clientH);
            svgElem.setAttribute("preserveAspectRatio", "xMidYMid meet");

            const tree = d3.tree().size([clientH, clientW]);
            const diagonal = d3.svg.diagonal().projection((d) => {
                return [d.y, d.x];
            });
            const update = (source) => {
                // Compute the new tree layout.
                const nodes = tree.nodes(root).reverse();
                const links = tree.links(nodes);
                // Normalize for fixed-depth.
                nodes.forEach((d) => {
                    d.y = d.depth * (clientW / 10);
                });
                // Update the nodes
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
                        const tName = d.name;
                        if (tName.length > maxTextLength) {
                            return tName.slice(0, maxTextLength) + "...";
                        }
                        return d.name;
                    });
                nodeEnter.append("title").text((d) => {
                    return d.children || d._children ? d.name : "Open tool - " + d.name;
                });
                // Transition nodes to their new position.
                const nodeUpdate = node
                    .transition()
                    .duration(duration)
                    .attr("transform", (d) => {
                        return "translate(" + d.y + "," + d.x + ")";
                    });
                nodeUpdate.select("circle").attr("r", 2.5);
                // Transition exiting nodes to the parent's new position.
                node.exit()
                    .transition()
                    .duration(duration)
                    .attr("transform", (d) => {
                        return "translate(" + source.y + "," + source.x + ")";
                    })
                    .remove();
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
                const tId = d.id;
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
            root.x0 = parseInt(clientH / 2);
            root.y0 = 0;
            root.children.forEach(collapse);
            update(root);
        },
    },
};
</script>

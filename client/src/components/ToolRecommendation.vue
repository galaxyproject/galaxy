<template>
    <div aria-labelledby="tool-recommendation-heading">
        <div v-if="!deprecated && showMessage" class="infomessagelarge">
            <h2 id="tool-recommendation-heading" class="h-sm">工具推荐</h2>
            您使用了 {{ getToolId }} 工具。为了进一步分析，您可以尝试使用以下推荐的工具。推荐的工具按其在工作流中的机器学习分析得分从高到低排序。因此，位于顶部的工具可能比底部的工具更有用。
            请点击以下推荐工具之一以查看其定义。
        </div>
        <div v-else-if="deprecated" class="warningmessagelarge">
            <h2 id="tool-recommendation-heading" class="h-sm">工具已弃用</h2>
            您使用了 {{ getToolId }} 工具。{{ deprecatedMessage }}
        </div>
        <div id="tool-recommendation" class="ui-tool-recommendation"></div>
    </div>
</template>

<script>
import { getDatatypesMapper } from "components/Datatypes";
import { getToolPredictions } from "components/Workflow/Editor/modules/services";
import { getCompatibleRecommendations } from "components/Workflow/Editor/modules/utilities";
import * as d3 from "d3";
import { getAppRoot } from "onload/loadConfig";

import { getShortToolId } from "@/utils/tool";

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
            return getShortToolId(this.toolId ?? "");
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
            const svgElem = svg.node().parentElement;
            const clientH = svgElem.clientHeight;
            const clientW = svgElem.clientWidth;
            const translateX = parseInt(clientW * 0.15);
            svgElem.setAttribute("viewBox", -translateX + " 0 " + 0.5 * clientW + " " + clientH);
            svgElem.setAttribute("preserveAspectRatio", "xMidYMid meet");
            const d3Tree = d3.tree().size([clientH, clientW]);
            root = d3.hierarchy(predictedTools, (d) => {
                return d.children;
            });
            root.x0 = parseInt(clientH / 2);
            root.y0 = 0;
            const collapse = (d) => {
                if (d.children) {
                    d._children = d.children;
                    d._children.forEach(collapse);
                    d.children = null;
                }
            };
            root.children.forEach(collapse);
            const diagonal = (s, d) => {
                const path = `M ${s.y} ${s.x}
                              C ${(s.y + d.y) / 2} ${s.x},
                              ${(s.y + d.y) / 2} ${d.x},
                              ${d.y} ${d.x}`;
                return path;
            };
            const click = (e, d) => {
                if (d.children) {
                    d._children = d.children;
                    d.children = null;
                } else {
                    d.children = d._children;
                    d._children = null;
                }
                if (d.parent == null) {
                    update(d);
                }
                const tId = d.data.id;
                if (tId !== undefined && tId !== "undefined" && tId !== null && tId !== "") {
                    document.location.href = `${getAppRoot()}tool_runner?tool_id=${tId}`;
                }
            };
            const update = (source) => {
                const predictedTools = d3Tree(root);
                const nodes = predictedTools.descendants();
                const links = predictedTools.descendants().slice(1);
                nodes.forEach((d) => {
                    d.y = d.depth * (clientW / 10);
                });
                const node = svg.selectAll("g.node").data(nodes, (d) => {
                    return d.id || (d.id = ++i);
                });
                const nodeEnter = node
                    .enter()
                    .append("g")
                    .attr("class", "node")
                    .attr("transform", (d) => {
                        return "translate(" + source.y0 + "," + source.x0 + ")";
                    })
                    .on("click", click);
                nodeEnter.append("circle").attr("class", "node").attr("r", 1e-6);
                nodeEnter
                    .append("text")
                    .attr("dy", ".35em")
                    .attr("x", (d) => {
                        return d.children || d._children ? -10 : 10;
                    })
                    .attr("text-anchor", (d) => {
                        return d.children || d._children ? "end" : "start";
                    })
                    .text((d) => {
                        const tName = d.data.name;
                        if (tName.length > maxTextLength) {
                            return tName.slice(0, maxTextLength) + "...";
                        }
                        return d.data.name;
                    });
                nodeEnter.append("title").text((d) => {
                    return d.children ? d.data.name : "Open tool - " + d.data.name;
                });
                const nodeUpdate = nodeEnter.merge(node);
                nodeUpdate
                    .transition()
                    .duration(duration)
                    .attr("transform", (d) => {
                        return "translate(" + d.y + "," + d.x + ")";
                    });
                nodeUpdate.select("circle.node").attr("r", 2.5);
                const nodeExit = node
                    .exit()
                    .transition()
                    .duration(duration)
                    .attr("transform", (d) => {
                        return "translate(" + source.y + "," + source.x + ")";
                    })
                    .remove();
                nodeExit.select("circle").attr("r", 1e-6);
                const link = svg.selectAll("path.link").data(links, (d) => {
                    return d.data.id;
                });
                const linkEnter = link
                    .enter()
                    .insert("path", "g")
                    .attr("class", "link")
                    .attr("d", (d) => {
                        const o = { x: source.x0, y: source.y0 };
                        return diagonal(o, o);
                    });
                const linkUpdate = linkEnter.merge(link);
                linkUpdate
                    .transition()
                    .duration(duration)
                    .attr("d", (d) => {
                        return diagonal(d, d.parent);
                    });
                link.transition().duration(duration).attr("d", diagonal);
                link.exit()
                    .transition()
                    .duration(duration)
                    .attr("d", (d) => {
                        const o = { x: source.x, y: source.y };
                        return diagonal(o, o);
                    })
                    .remove();
                nodes.forEach((d) => {
                    d.x0 = d.x;
                    d.y0 = d.y;
                });
            };
            update(root);
        },
    },
};
</script>

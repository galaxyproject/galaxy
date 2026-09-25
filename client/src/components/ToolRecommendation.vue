<script setup lang="ts">
import * as d3 from "d3";
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router/composables";

import { getDatatypesMapper } from "@/components/Datatypes";
import { getToolPredictions } from "@/components/Workflow/Editor/modules/services";
import { getCompatibleRecommendations, type PredictedToolChild } from "@/components/Workflow/Editor/modules/utilities";
import { errorMessageAsString } from "@/utils/simple-error";
import { getShortToolId } from "@/utils/tool";

/** Shape of the (currently mocked) `getToolPredictions` response. */
interface ToolPredictionsResponse {
    current_tool: string;
    predicted_data: {
        is_deprecated: boolean;
        message: string;
        name: string;
        o_extensions: string[];
        children: PredictedToolChild[];
    };
}

/** Tree data handed to d3: a root node (no `id`) whose children are recommendations
 * already filtered down to compatible tools by `getCompatibleRecommendations`. */
interface PredictedTools {
    id?: string;
    o_extensions?: string[];
    name: string;
    children?: PredictedTools[];
}
type TreeNode = d3.HierarchyPointNode<PredictedTools> & { x0: number; y0: number; _children?: TreeNode[] };

const props = defineProps<{
    toolId: string;
}>();

const router = useRouter();

const deprecated = ref(false);
const deprecatedMessage = ref("");
const errorMessage = ref<string | null>(null);
const showMessage = ref(false);
const toolRecommendation = ref<HTMLDivElement | null>(null);

async function loadRecommendations() {
    const toolId = getShortToolId(props.toolId);
    const requestData = {
        tool_sequence: toolId,
    };
    try {
        const responsePred = (await getToolPredictions(requestData)) as ToolPredictionsResponse | null | undefined;
        const datatypesMapper = await getDatatypesMapper(false);
        if (responsePred) {
            const predData = responsePred.predicted_data;
            deprecated.value = predData.is_deprecated;
            deprecatedMessage.value = predData.message;
            if (predData.children.length > 0) {
                const outputDatatypes = predData.o_extensions;
                const children = predData.children;
                const compatibleTools = getCompatibleRecommendations(children, outputDatatypes, datatypesMapper);
                if (compatibleTools.length > 0 && deprecated.value === false) {
                    showMessage.value = true;
                    const filteredData: PredictedTools = {
                        o_extensions: predData.o_extensions,
                        name: predData.name,
                        children: compatibleTools,
                    };
                    renderD3Tree(filteredData);
                }
            }
        }

        errorMessage.value = null;
    } catch (error) {
        errorMessage.value = errorMessageAsString(error);
    }
}

function renderD3Tree(predictedTools: PredictedTools) {
    let i = 0;
    const duration = 750;
    const maxTextLength = 20;
    const clientH = toolRecommendation.value?.clientHeight ?? 0;
    const clientW = toolRecommendation.value?.clientWidth ?? 0;
    const svg = d3.select(toolRecommendation.value).append("svg").attr("class", "tree-size").append("g");
    const svgElem = svg.node()?.parentElement;
    const translateX = Math.trunc(clientW * 0.15);
    svgElem?.setAttribute("viewBox", -translateX + " 0 " + 0.5 * clientW + " " + clientH);
    svgElem?.setAttribute("preserveAspectRatio", "xMidYMid meet");
    const d3Tree = d3.tree<PredictedTools>().size([clientH, clientW]);
    const root: TreeNode = d3.hierarchy(predictedTools, (d) => {
        return d.children;
    }) as TreeNode;
    root.x0 = Math.trunc(clientH / 2);
    root.y0 = 0;
    const collapse = (d: TreeNode) => {
        if (d.children) {
            d._children = d.children;
            d._children.forEach(collapse);
            d.children = undefined;
        }
    };
    root.children?.forEach(collapse);
    const diagonal = (s: { x: number; y: number }, d: { x: number; y: number }) => {
        const path = `M ${s.y} ${s.x}
                        C ${(s.y + d.y) / 2} ${s.x},
                        ${(s.y + d.y) / 2} ${d.x},
                        ${d.y} ${d.x}`;
        return path;
    };
    const click = (_event: PointerEvent, d: TreeNode) => {
        if (d.children) {
            d._children = d.children;
            d.children = undefined;
        } else {
            d.children = d._children;
            d._children = undefined;
        }
        if (d.parent == null) {
            update(d);
        }
        const tId = d.data.id;
        if (tId !== undefined && tId !== "undefined" && tId !== null && tId !== "") {
            router.push(`/?tool_id=${tId}`);
        }
    };
    const update = (source: TreeNode) => {
        // `d3Tree` lays the tree out in place on `root`'s existing node objects (our `TreeNode`s),
        // so its return value is the same graph, just now with real x/y coordinates.
        const predictedTools = d3Tree(root) as TreeNode;
        const nodes = predictedTools.descendants() as TreeNode[];
        const links = nodes.slice(1);
        nodes.forEach((d) => {
            d.y = d.depth * (clientW / 10);
        });
        const node = svg.selectAll<SVGGElement, TreeNode>("g.node").data(nodes, (d) => {
            // `HierarchyNode.id` is typed readonly (meant to be set via a layout's `.id()`
            // accessor), but assigning it directly here is a standard d3 idiom for giving each
            // node a stable join key on first render.
            return d.id || ((d as { id?: string | number }).id = ++i);
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
        const link = svg.selectAll<SVGPathElement, TreeNode>("path.link").data(links, (d) => {
            return d.data.id ?? d.data.name;
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
                // `links` is every node except the root (`nodes.slice(1)`), so `d.parent` is
                // always defined here; the fallback only satisfies the nullable type.
                return diagonal(d, d.parent ?? d);
            });
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
}

onMounted(() => {
    loadRecommendations();
});
</script>

<template>
    <div v-if="!errorMessage && (deprecated || showMessage)">
        <h2 id="tool-recommendation-heading" class="h-sm">Tool recommendation</h2>
        <div v-if="!deprecated && showMessage">
            You have used {{ getShortToolId(props.toolId) }} tool. For further analysis, you could try using the
            following/recommended tools. The recommended tools are shown in the decreasing order of their scores
            predicted using machine learning analysis on workflows. Therefore, tools at the top may be more useful than
            the ones at the bottom. Please click on one of the following/recommended tools to open its definition.
        </div>
        <div v-else-if="deprecated" class="warningmessagelarge">
            <h2 class="h-sm">Tool deprecated</h2>
            You have used {{ getShortToolId(props.toolId) }} tool. {{ deprecatedMessage }}
        </div>
        <div ref="toolRecommendation" class="ui-tool-recommendation"></div>
    </div>
</template>

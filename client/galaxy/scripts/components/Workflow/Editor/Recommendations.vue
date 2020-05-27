<template>
    <div class="workflow-recommendations">
        <div class="header-background">
            <h4>{{ popoverHeaderText }}</h4>
        </div>
        <LoadingSpan v-if="showLoading" message="Loading recommendations" />
        <div v-if="compatibleTools.length > 0 && !isDeprecated">
            <div v-for="tool in compatibleTools" :key="tool.id">
                <i class="fa mr-1 fa-wrench"></i>
                <a href="#" title="Open tool" :id="tool.id" @click="$emit('onCreate', tool.id, $event)">
                    {{ tool.name }}
                </a>
            </div>
        </div>
        <div v-else-if="isDeprecated">
            {{ deprecatedMessage }}
        </div>
        <div v-if="compatibleTools.length === 0 && !showLoading">
            {{ noRecommendationsMessage }}
        </div>
    </div>
</template>

<script>
import { getToolPredictions } from "./modules/services";
import LoadingSpan from "components/LoadingSpan";
import _l from "utils/localization";

export default {
    components: {
        LoadingSpan,
    },
    props: {
        node: {
            type: Object,
            required: true,
        },
    },
    data() {
        return {
            compatibleTools: [],
            isDeprecated: false,
            popoverHeaderText: _l("Tool recommendations"),
            noRecommendationsMessage: _l("No tool recommendations"),
            deprecatedMessage: "",
            showLoading: true,
        };
    },
    created() {
        this.loadRecommendations();
    },
    methods: {
        getToolId(toolId) {
            if (toolId !== undefined && toolId !== null && toolId.indexOf("/") > -1) {
                const toolIdSlash = toolId.split("/");
                toolId = toolIdSlash[toolIdSlash.length - 2];
            }
            return toolId;
        },
        getWorkflowPath(wfSteps, currentNodeId) {
            const steps = {};
            const stepNames = {};
            for (const stpIdx in wfSteps.steps) {
                const step = wfSteps.steps[stpIdx];
                const inputConnections = step.input_connections;
                stepNames[step.id] = this.getToolId(step.content_id);
                for (const icIdx in inputConnections) {
                    const ic = inputConnections[icIdx];
                    if (ic !== null && ic !== undefined) {
                        const prevConn = [];
                        for (const conn of ic) {
                            prevConn.push(conn.id.toString());
                        }
                        steps[step.id.toString()] = prevConn;
                    }
                }
            }
            // recursive call to determine path
            function readPaths(nodeId, ph) {
                for (const st in steps) {
                    if (parseInt(st) === parseInt(nodeId)) {
                        const parentId = parseInt(steps[st][0]);
                        if (parentId !== undefined && parentId !== null) {
                            ph.push(parentId);
                            if (steps[parentId] !== undefined && steps[parentId] !== null) {
                                readPaths(parentId, ph);
                            }
                        }
                    }
                }
                return ph;
            }
            let ph = [];
            const stepNameList = [];
            ph.push(currentNodeId);
            ph = readPaths(currentNodeId, ph);
            for (const sIdx of ph) {
                const sName = stepNames[sIdx.toString()];
                if (sName !== undefined && sName !== null) {
                    stepNameList.push(sName);
                }
            }
            return stepNameList.join(",");
        },
        loadRecommendations() {
            const workflowSimple = this.node.app.to_simple();
            const node = this.node;
            const toolSequence = this.getWorkflowPath(workflowSimple, node.id);
            const requestData = { tool_sequence: toolSequence };
            getToolPredictions(requestData).then((responsePred) => {
                const predictedData = responsePred.predicted_data;
                const outputDatatypes = predictedData.o_extensions;
                const predictedDataChildren = predictedData.children;
                const app = this.node.app;
                this.isDeprecated = predictedData.is_deprecated;
                this.deprecatedMessage = predictedData.message;
                if (predictedDataChildren.length > 0) {
                    const cTools = [];
                    for (const nameObj of predictedDataChildren.entries()) {
                        const t = {};
                        const inputDatatypes = nameObj[1].i_extensions;
                        for (const outT of outputDatatypes.entries()) {
                            for (const inTool of inputDatatypes.entries()) {
                                if (
                                    app.isSubType(outT[1], inTool[1]) === true ||
                                    outT[1] === "input" ||
                                    outT[1] === "_sniff_" ||
                                    outT[1] === "input_collection"
                                ) {
                                    t.id = nameObj[1].tool_id;
                                    t.name = nameObj[1].name;
                                    cTools.push(t);
                                    break;
                                }
                            }
                        }
                    }
                    this.compatibleTools = cTools;
                }
                this.showLoading = false;
            });
        },
    },
};
</script>

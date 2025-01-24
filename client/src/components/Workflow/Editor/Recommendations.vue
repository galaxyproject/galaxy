<template>
    <div class="workflow-recommendations">
        <div class="header-background">
            <h2 class="h-sm">{{ popoverHeaderText }}</h2>
        </div>
        <LoadingSpan v-if="showLoading" message="Loading recommendations" />
        <div v-if="compatibleTools.length > 0 && !isDeprecated">
            <div v-for="tool in compatibleTools" :key="tool.id">
                <i class="fa mr-1 fa-wrench"></i>
                <a :id="tool.id" href="#" title="Open tool" @click="$emit('onCreate', tool.id, tool.name, $event)">{{
                    tool.name
                }}</a>
            </div>
        </div>
        <div v-else-if="isDeprecated">{{ deprecatedMessage }}</div>
        <div v-if="compatibleTools.length === 0 && !showLoading">{{ noRecommendationsMessage }}</div>
    </div>
</template>

<script>
import LoadingSpan from "components/LoadingSpan";
import _l from "utils/localization";

import { useWorkflowStores } from "@/composables/workflowStores";
import { getShortToolId } from "@/utils/tool";

import { getToolPredictions } from "./modules/services";
import { getCompatibleRecommendations } from "./modules/utilities";

export default {
    components: {
        LoadingSpan,
    },
    props: {
        stepId: {
            type: Number,
            required: true,
        },
        datatypesMapper: {
            type: Object,
            required: true,
        },
    },
    setup() {
        const { stepStore } = useWorkflowStores();
        return { stepStore };
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
            return getShortToolId(toolId ?? "");
        },
        getWorkflowPath(currentNodeId) {
            const steps = {};
            const stepNames = {};
            Object.values(this.stepStore.steps).map((step) => {
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
            });
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
            const toolSequence = this.getWorkflowPath(this.stepId);
            const requestData = { tool_sequence: toolSequence };
            getToolPredictions(requestData).then((responsePred) => {
                const predictedData = responsePred.predicted_data;
                const outputDatatypes = predictedData.o_extensions;
                const predictedDataChildren = predictedData.children;
                this.isDeprecated = predictedData.is_deprecated;
                this.deprecatedMessage = predictedData.message;
                if (predictedDataChildren.length > 0) {
                    this.compatibleTools = getCompatibleRecommendations(
                        predictedDataChildren,
                        outputDatatypes,
                        this.datatypesMapper
                    );
                }
                this.showLoading = false;
            });
        },
    },
};
</script>

<style scoped lang="scss">
@import "theme/blue.scss";

.workflow-recommendations {
    display: block;
    height: 30rem;

    .header-background {
        border-bottom: solid 1px $brand-primary;
        margin-bottom: 0.5rem;
    }
}
</style>

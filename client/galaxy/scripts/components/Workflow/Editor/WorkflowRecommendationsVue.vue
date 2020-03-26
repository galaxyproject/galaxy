<template>
    <div class="modal ui-modal wf-recommendation-view">
        <div class="modal-backdrop fade in"></div>
        <div class="modal-dialog wf-tools-dialog">
            <div class="modal-content wf-tool-content">
                <div class="modal-header wf-tools-background" :title="modalHeaderToolTip">
                    <h4>{{ modalHeaderTitle }}</h4>
                </div>
                <div class="modal-body wf-tools-body">
                    <div>
                        {{ loadingMessage }}
                    </div>
                    <div v-if="compatibleTools.length > 0 && !isDeprecated">
                        <div v-for="tool in compatibleTools">
                            <i class="fa mr-1 fa-wrench"></i>
                            <a href="#" title="Open tool" :id="tool.id" v-on:click="createTool(tool.id)">
                                {{ tool.name }}
                            </a>
                        </div>
                        <br />
                    </div>
                    <div v-else-if="isDeprecated">
                        {{ deprecatedMessage }}
                    </div>
                    <div v-else>
                        {{ noRecommendationsMessage }}
                    </div>
                </div>
                <div class="modal-footer">
                    <div class="buttons">
                        <button v-on:click="closeModal" title="Cancel" class="wf-tools-background">Cancel</button>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import { getAppRoot } from "onload/loadConfig";
import axios from "axios";
import { getModule } from "./services";
import _l from "utils/localization";

export default {
    props: {
        workflowManager: {
            type: Object
        },
        toolSequence: {
            type: String
        }
    },
    data() {
        return {
            modalHeaderTitle: _l("Tool Recommendations"),
            modalHeaderToolTip: _l(
                "The recommended tools are shown in the decreasing order of their scores predicted using machine learning analysis on workflows. A tool with a higher score (closer to 100%) may fit better as the following tool than a tool with a lower score. Please click on one of the following/recommended tools to have it on the workflow editor."
            ),
            compatibleTools: [],
            isDeprecated: false,
            noRecommendationsMessage: "",
            deprecatedMessage: "",
            loadingMessage: "Loading recommendations ..."
        };
    },
    created() {
        this.loadRecommendations();
    },
    computed: {},
    methods: {
        async loadRecommendations() {
            const response = await axios.post(`${getAppRoot()}api/workflows/get_tool_predictions`, {
                tool_sequence: this.toolSequence
            });
            const predictedData = response.data.predicted_data;
            const outputDatatypes = predictedData.o_extensions;
            const predictedDataChildren = predictedData.children;
            const app = this.workflowManager.node.app;
            this.isDeprecated = predictedData.is_deprecated;
            this.deprecatedMessage = predictedData.message;
            if (predictedDataChildren.length > 0) {
                let cTools = [];
                for (const [index, name_obj] of predictedDataChildren.entries()) {
                    let t = {};
                    const inputDatatypes = name_obj.i_extensions;
                    for (const out_t of outputDatatypes.entries()) {
                        for (const in_t of inputDatatypes.entries()) {
                            if (
                                app.isSubType(out_t[1], in_t[1]) === true ||
                                out_t[1] === "input" ||
                                out_t[1] === "_sniff_" ||
                                out_t[1] === "input_collection"
                            ) {
                                t.id = name_obj.tool_id;
                                t.name = name_obj.name;
                                cTools.push(t);
                                break;
                            }
                        }
                    }
                }
                this.loadingMessage = "";
                this.compatibleTools = cTools;
            } else {
                this.noRecommendationsMessage = "No tool recommendations";
            }
        },
        closeModal() {
            this.$el.remove();
        },
        createTool(tId) {
            const app = this.workflowManager.node.app;
            const requestData = {
                type: "tool",
                tool_id: tId,
                _: "true"
            };
            getModule(requestData).then(response => {
                const node = app.create_node("tool", response.name, tId);
                app.set_node(node, response);
                this.closeModal();
            });
        }
    }
};
</script>

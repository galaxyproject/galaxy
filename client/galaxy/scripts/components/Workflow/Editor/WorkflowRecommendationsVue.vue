<template>
    <div class="modal ui-modal modal-tool-recommendation" style="display: block;">
        <div class="modal-backdrop fade in">
        </div>
        <div class="modal-dialog" style="width: 260px;">
            <div class="modal-content">
                <div class="modal-header" title="The recommended tools are shown in the decreasing order of their scores predicted using machine learning analysis on workflows. A tool with a higher score (closer to 100%) may fit better as the following tool than a tool with a lower score. Please click on one of the following/recommended tools to have it on the workflow editor.">
                    <h4 class="title" tabindex="0">Recommended tools</h4>
                </div>
                <div class="modal-body" style="height: 280px; overflow: auto;">
                    <i class="fa mr-1 fa-wrench"></i>
                    <a href="#" title="Click to open the tool" class="pred-tool panel-header-button" id="Grep1">Select (100%)</a>
                        
                    <i class="fa mr-1 fa-wrench"></i>
                    <a href="#" title="Click to open the tool" class="pred-tool panel-header-button" id="Grep1">Select (100%)</a>
                </div>
                <div class="modal-footer">
                    <div class="buttons">
                        <button id="button-0">Close</button>&nbsp;
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>

import { getAppRoot } from "onload/loadConfig";
import axios from "axios";
import _l from "utils/localization";

export default {
    props: {
        workflowManager: {
            type: Object,
        },
        toolSequence: {
            type: String
        }
    },
    data() {
        return {
        };
    },
    created() {
        this.loadRecommendations();
    },
    computed: {
    },
    methods: {
        loadRecommendations() {
            console.log("loaded");
            console.log(this.workflowManager);
            console.log(this.toolSequence);
            axios
                .post(`${getAppRoot()}api/workflows/get_tool_predictions`, {
                    tool_sequence: this.toolSequence,
                })
                .then((data) => {
                    console.log(data);
                });
        },
    },
};
</script>

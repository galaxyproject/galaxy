<template>
    <div>
        <div class="donemessagelarge">
            <p>
                Successfully invoked workflow <b>{{ workflowName }}</b
                ><em v-if="multipleInvocations"> - {{ timesExecuted }} times</em>.
            </p>
            <p v-if="multipleInvocations">
                This workflow will generate results in multiple histories. You can observe progress in the
                <a :href="historyTarget">history multi-view</a>.
            </p>
            <p v-else-if="wasNewHistoryTarget">
                This workflow will generate results in a new history.
                <a class="workflow-new-history-target-link" :href="historyTarget">Switch to that history now</a>.
            </p>
            <p v-else>You can check the status of queued jobs and view the resulting data the History panel.</p>
        </div>
        <workflow-invocation-state
            v-for="(invocation, index) in invocations"
            :key="invocation.id"
            :index="index"
            :invocation-id="invocation.id" />
        <div id="webhook-view"></div>
    </div>
</template>

<script>
import { WorkflowInvocationState } from "components/WorkflowInvocationState";
import Webhooks from "mvc/webhooks";
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";

export default {
    components: {
        WorkflowInvocationState,
    },
    props: {
        workflowName: {
            type: String,
            required: true,
        },
        invocations: {
            type: Array,
            required: true,
        },
    },
    data() {
        return {
            refreshHistoryTimeout: null,
        };
    },
    computed: {
        timesExecuted() {
            return this.invocations.length;
        },
        multipleInvocations() {
            return this.timesExecuted > 1;
        },
        historyTarget() {
            if (this.multipleInvocations) {
                return `${getAppRoot()}history/view_multiple`;
            } else {
                return `${getAppRoot()}history/switch_to_history?hist_id=${this.invocations[0].history_id}`;
            }
        },
        wasNewHistoryTarget() {
            if (this.invocations.length < 1) {
                return false;
            }
            const Galaxy = getGalaxyInstance();
            return (
                (this.invocations[0].history_id &&
                    Galaxy.currHistoryPanel &&
                    Galaxy.currHistoryPanel.model.id != this.invocations[0].history_id) ||
                false
            );
        },
    },
    mounted() {
        new Webhooks.WebhookView({
            type: "workflow",
            toolId: null,
            toolVersion: null,
        });
        this._refreshHistory();
    },
    methods: {
        _refreshHistory() {
            // remove when disabling backbone history
            const Galaxy = getGalaxyInstance();
            var history = Galaxy && Galaxy.currHistoryPanel && Galaxy.currHistoryPanel.model;
            if (this.refreshHistoryTimeout) {
                window.clearTimeout(this.refreshHistoryTimeout);
            }
            if (history && history.refresh) {
                history.refresh().success(() => {
                    if (history.numOfUnfinishedShownContents() === 0) {
                        this.refreshHistoryTimeout = window.setTimeout(() => {
                            this._refreshHistory();
                        }, history.UPDATE_DELAY);
                    }
                });
            }
        },
    },
};
</script>

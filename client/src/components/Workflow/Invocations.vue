<template>
    <div class="invocations-list">
        <h2 class="mb-3">
            <span id="invocations-title">Workflow Invocations</span>
        </h2>
        <b-alert variant="info" show v-if="headerMessage">
            {{ headerMessage }}
        </b-alert>
        <loading-span v-if="loading" message="Loading workflow invocations" />
        <div v-else>
            <b-alert id="no-invocations" v-if="!invocationItemsComputed.length" variant="info" show>
                {{ noInvocationsMessage }}
            </b-alert>
            <b-table
                v-else
                :fields="invocationFields"
                :items="invocationItemsComputed"
                v-model="invocationItemsModel"
                hover
                striped
                caption-top
                :busy="loading"
                fixed
                class="invocations-table"
            >
                <template v-slot:row-details="row">
                    <b-card>
                        <small class="float-right" :data-invocation-id="row.item.id">
                            <b>Invocation: {{ row.item.id }}</b>
                        </small>
                        <workflow-invocation-state
                            :invocation-id="row.item.id"
                            @invocation-cancelled="$emit('reload-invocations')"
                        />
                    </b-card>
                </template>
                <template v-slot:cell(expand)="data">
                    <b-link
                        v-b-tooltip.hover.bottom
                        title="Show Invocation Details"
                        class="btn-sm fa fa-chevron-down"
                        v-if="!data.detailsShowing"
                        @click.stop="swapRowDetails(data)"
                    />
                    <b-link
                        v-b-tooltip.hover.bottom
                        title="Hide Invocation Details"
                        class="btn-sm fa fa-chevron-up"
                        v-if="data.detailsShowing"
                        @click.stop="swapRowDetails(data)"
                    />
                </template>
                <template v-slot:cell(workflow_id)="data">
                    <b-link
                        class="toggle-invocation-details"
                        v-b-tooltip
                        :title="getWorkflowNameByInstanceId(data.item.workflow_id)"
                        href="#"
                        @click.stop="swapRowDetails(data)"
                    >
                        <b>{{ getWorkflowNameByInstanceId(data.item.workflow_id) }}</b>
                    </b-link>
                </template>
                <template v-slot:cell(history_id)="data">
                    <b-link
                        id="switch-to-history"
                        v-b-tooltip
                        title="Switch to History"
                        href="#"
                        @click.stop="switchHistory(data.item.history_id)"
                    >
                        <b>{{ getHistoryNameById(data.item.history_id) }}</b>
                    </b-link>
                </template>
                <template v-slot:cell(create_time)="data">
                    <UtcDate :date="data.value" mode="elapsed" />
                </template>
                <template v-slot:cell(update_time)="data">
                    <UtcDate :date="data.value" mode="elapsed" />
                </template>
                <template v-slot:cell(execute)="data">
                    <b-button
                        v-b-tooltip.hover.bottom
                        id="run-workflow"
                        title="Run Workflow"
                        class="workflow-run btn-sm btn-primary fa fa-play"
                        @click.stop="executeWorkflow(getWorkflowByInstanceId(data.item.workflow_id).id)"
                    />
                </template>
            </b-table>
        </div>
    </div>
</template>

<script>
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";
import { WorkflowInvocationState } from "components/WorkflowInvocationState";
import UtcDate from "components/UtcDate";
import LoadingSpan from "components/LoadingSpan";
import { mapCacheActions } from "vuex-cache";
import { mapGetters } from "vuex";

export default {
    components: {
        UtcDate,
        WorkflowInvocationState,
        LoadingSpan,
    },
    props: {
        invocationItems: { type: Array, default: () => [] },
        loading: { type: Boolean, default: true },
        noInvocationsMessage: { type: String, default: "No Workflow Invocations to display" },
        headerMessage: { type: String, default: "" },
        ownerGrid: { type: Boolean, default: true },
    },
    data() {
        const fields = [
            { key: "expand", label: "", class: "col-button" },
            { key: "workflow_id", label: "Workflow", class: "col-name" },
            { key: "history_id", label: "History", class: "col-history" },
            { key: "create_time", label: "Invoked", class: "col-small" },
            { key: "update_time", label: "Updated", class: "col-small" },
            { key: "state", class: "col-small" },
            { key: "execute", label: "", class: "col-button" },
        ];
        return {
            invocationItemsModel: [],
            invocationFields: fields,
            status: "",
        };
    },
    computed: {
        ...mapGetters(["getWorkflowNameByInstanceId", "getWorkflowByInstanceId", "getHistoryNameById"]),
        invocationItemsComputed() {
            return this.computeItems(this.invocationItems);
        },
    },
    methods: {
        ...mapCacheActions(["fetchWorkflowForInstanceId", "fetchHistoryForId"]),
        computeItems(items) {
            return items.map((invocation) => {
                if (this.ownerGrid) {
                    this.fetchWorkflowForInstanceId(invocation["workflow_id"]);
                    this.fetchHistoryForId(invocation["history_id"]);
                }
                return {
                    id: invocation["id"],
                    create_time: invocation["create_time"],
                    update_time: invocation["update_time"],
                    workflow_id: invocation["workflow_id"],
                    history_id: invocation["history_id"],
                    state: invocation["state"],
                    _showDetails: false,
                };
            });
        },
        swapRowDetails(row) {
            row.toggleDetails();
        },
        executeWorkflow: function (workflowId) {
            window.location = `${getAppRoot()}workflows/run?id=${workflowId}`;
        },
        switchHistory(historyId) {
            const Galaxy = getGalaxyInstance();
            Galaxy.currHistoryPanel.switchToHistory(historyId);
        },
    },
};
</script>
<style scoped>
.invocations-table {
    min-width: 40rem;
}
.table::v-deep .col-name {
    overflow: hidden;
    white-space: nowrap;
    text-overflow: ellipsis;
}
.table::v-deep .col-history {
    width: 20%;
}
.table::v-deep .col-small {
    width: 100px;
}
.table::v-deep .col-button {
    width: 50px;
}
</style>

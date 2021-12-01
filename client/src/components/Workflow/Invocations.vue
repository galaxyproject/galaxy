<template>
    <div class="invocations-list">
        <h2 class="mb-3">
            <span id="invocations-title">Workflow Invocations</span>
        </h2>
        <b-alert variant="info" show v-if="headerMessage">
            {{ headerMessage }}
        </b-alert>
        <b-table
            id="invocation-list-table"
            :fields="invocationFields"
            :items="provider"
            v-model="invocationItemsModel"
            :per-page="perPage"
            :current-page="currentPage"
            hover
            striped
            caption-top
            fixed
            show-empty
            class="invocations-table"
        >
            <template v-slot:empty>
                <b-alert id="no-invocations" variant="info" show>
                    {{ noInvocationsMessage }}
                </b-alert>
            </template>
            <template v-slot:row-details="row">
                <b-card>
                    <small class="float-right" :data-invocation-id="row.item.id">
                        <b>Invocation: {{ row.item.id }}</b>
                    </small>
                    <workflow-invocation-state :invocation-id="row.item.id" @invocation-cancelled="refresh" />
                </b-card>
            </template>
            <template v-slot:cell(expand)="data">
                <b-link
                    v-b-tooltip.hover.top
                    title="Show Invocation Details"
                    class="btn-sm fa fa-chevron-down toggle-invocation-details"
                    v-if="!data.detailsShowing"
                    @click.stop="swapRowDetails(data)"
                />
                <b-link
                    v-b-tooltip.hover.top
                    title="Hide Invocation Details"
                    class="btn-sm fa fa-chevron-up toggle-invocation-details"
                    v-if="data.detailsShowing"
                    @click.stop="swapRowDetails(data)"
                />
            </template>
            <template v-slot:cell(workflow_id)="data">
                <div v-b-tooltip.hover.top :title="getWorkflowNameByInstanceId(data.item.workflow_id)" class="truncate">
                    <b-link href="#" @click.stop="swapRowDetails(data)">
                        <b>{{ getWorkflowNameByInstanceId(data.item.workflow_id) }}</b>
                    </b-link>
                </div>
            </template>
            <template v-slot:cell(history_id)="data">
                <div
                    v-b-tooltip.hover.top.html
                    :title="`<b>Switch to History:</b><br>${getHistoryNameById(data.item.history_id)}`"
                    class="truncate"
                >
                    <b-link id="switch-to-history" href="#" @click.stop="switchHistory(data.item.history_id)">
                        <b>{{ getHistoryNameById(data.item.history_id) }}</b>
                    </b-link>
                </div>
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
        <b-pagination
            v-model="currentPage"
            :per-page="perPage"
            :total-rows="rows"
            aria-controls="invocation-list-table"
        ></b-pagination>
    </div>
</template>

<script>
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";
import { invocationsProvider } from "components/providers/InvocationsProvider";
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
        noInvocationsMessage: { type: String, default: "No Workflow Invocations to display" },
        headerMessage: { type: String, default: "" },
        ownerGrid: { type: Boolean, default: true },
    },
    data() {
        const fields = [
            { key: "expand", label: "", class: "col-button" },
            { key: "workflow_id", label: "Workflow", class: "col-name" },
            { key: "history_id", label: "History", class: "col-history" },
            { key: "create_time", label: "Invoked", class: "col-small", sortable: true },
            { key: "update_time", label: "Updated", class: "col-small", sortable: true },
            { key: "state", class: "col-small" },
            { key: "execute", label: "", class: "col-button" },
        ];
        return {
            invocationItems: [],
            invocationItemsModel: [],
            invocationFields: fields,
            status: "",
            currentPage: 1,
            perPage: 50,
            rows: 0,
        };
    },
    computed: {
        ...mapGetters([
            "getWorkflowNameByInstanceId",
            "getWorkflowByInstanceId",
            "getHistoryById",
            "getHistoryNameById",
        ]),
        apiUrl() {
            return `${getAppRoot()}api/invocations`;
        },
    },
    watch: {
        invocationItems: function (promise) {
            promise.then((invocations) => {
                const historyIds = new Set();
                const workflowIds = new Set();
                invocations.map((invocation) => {
                    historyIds.add(invocation.history_id);
                    workflowIds.add(invocation.workflow_id);
                });
                historyIds.forEach(
                    (history_id) => this.getHistoryById(history_id) || this.fetchHistoryForId(history_id)
                );
                workflowIds.forEach(
                    (workflow_id) =>
                        this.getWorkflowByInstanceId(workflow_id) || this.fetchWorkflowForInstanceId(workflow_id)
                );
            });
        },
    },
    methods: {
        ...mapCacheActions(["fetchWorkflowForInstanceId", "fetchHistoryForId"]),
        provider(ctx) {
            ctx.apiUrl = this.apiUrl;
            const extraParams = this.ownerGrid ? {} : { include_terminal: false };
            this.invocationItems = invocationsProvider(ctx, this.setRows, extraParams);
            return this.invocationItems;
        },
        refresh() {
            this.$root.$emit("bv::refresh::table", "invocation-list-table");
        },
        setRows(data) {
            this.rows = data.headers.total_matches;
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
    width: 40%;
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
.table::v-deep .truncate {
    overflow: hidden;
    white-space: nowrap;
    text-overflow: ellipsis;
}
</style>

<template>
    <div class="invocations-list">
        <h2 class="mb-3" v-if="showTitle">
            <span id="invocations-title">{{ title }}</span>
        </h2>
        <b-alert v-if="headerMessage && showTitle" variant="info" show>
            {{ headerMessage }}
        </b-alert>
        <b-alert class="index-grid-message" :variant="messageVariant" :show="showMessage">{{ message }}</b-alert>
        <b-table
            v-bind="indexTableAttrs"
            v-model="invocationItemsModel"
            :fields="invocationFields"
            :items="provider"
            class="invocations-table">
            <template v-slot:empty>
                <loading-span v-if="loading" message="Loading workflow invocations" />
                <b-alert v-else id="no-invocations" variant="info" show>
                    {{ effectiveNoInvocationsMessage }}
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
                    v-if="!data.detailsShowing"
                    v-b-tooltip.hover.top
                    title="Show Invocation Details"
                    class="btn-sm fa fa-chevron-down toggle-invocation-details"
                    @click.stop="swapRowDetails(data)" />
                <b-link
                    v-if="data.detailsShowing"
                    v-b-tooltip.hover.top
                    title="Hide Invocation Details"
                    class="btn-sm fa fa-chevron-up toggle-invocation-details"
                    @click.stop="swapRowDetails(data)" />
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
                    class="truncate">
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
                <WorkflowRunButton :id="getWorkflowByInstanceId(data.item.workflow_id).id" :root="root" />
            </template>
        </b-table>
        <b-pagination
            v-show="rows >= perPage"
            v-model="currentPage"
            class="gx-invocations-grid-pager"
            v-bind="paginationAttrs"></b-pagination>
    </div>
</template>

<script>
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";
import { invocationsProvider } from "components/providers/InvocationsProvider";
import { WorkflowInvocationState } from "components/WorkflowInvocationState";
import WorkflowRunButton from "./WorkflowRunButton.vue";
import UtcDate from "components/UtcDate";
import { mapCacheActions } from "vuex-cache";
import { mapGetters } from "vuex";
import paginationMixin from "./paginationMixin";

const WORKFLOW_FIELD = { key: "workflow_id", label: "Workflow", class: "col-name" };
const HISTORY_FIELD = { key: "history_id", label: "History", class: "col-history" };
const STATE_FIELD = { key: "state", class: "col-small" };
const UPDATE_TIME_FIELD = { key: "update_time", label: "Updated" };
const CREATE_TIME_FIELD = { key: "create_time", label: "Invoked", complex: true };
const EXECUTE_FIELD = { key: "execute", label: "", class: "col-button" };
const EXPAND_FIELD = { key: "expand", label: "", class: "col-button" };
const FIELDS = [
    EXPAND_FIELD,
    WORKFLOW_FIELD,
    HISTORY_FIELD,
    STATE_FIELD,
    UPDATE_TIME_FIELD,
    CREATE_TIME_FIELD,
    EXECUTE_FIELD,
];

export default {
    components: {
        UtcDate,
        WorkflowInvocationState,
        WorkflowRunButton,
    },
    mixins: [paginationMixin],
    props: {
        noInvocationsMessage: { type: String, default: "No Workflow Invocations to display" },
        headerMessage: { type: String, default: "" },
        ownerGrid: { type: Boolean, default: true },
        userId: { type: String, default: null },
        storedWorkflowId: { type: String, default: null },
        storedWorkflowName: { type: String, default: null },
        showTitle: { type: Boolean, default: true },
        simplified: { type: Boolean, default: false },
    },
    data() {
        const fields = FIELDS.filter((field) => (!this.simplified || !field.complex ? true : false));
        return {
            tableId: "invocation-list-table",
            invocationItems: [],
            invocationItemsModel: [],
            invocationFields: fields,
            perPage: this.rowsPerPage(50),
            root: getAppRoot(),
        };
    },
    computed: {
        ...mapGetters(["getWorkflowNameByInstanceId", "getWorkflowByInstanceId"]),
        ...mapGetters("history", ["getHistoryById", "getHistoryNameById"]),
        title() {
            let title = `Workflow Invocations`;
            if (this.storedWorkflowName) {
                title += ` for ${this.storedWorkflowName}`;
            }
            return title;
        },
        effectiveNoInvocationsMessage() {
            let message = this.noInvocationsMessage;
            if (this.storedWorkflowName) {
                message += ` for ${this.storedWorkflowName}`;
            }
            return message;
        },
    },
    watch: {
        invocationItems: function (invocations) {
            if (invocations) {
                const historyIds = new Set();
                const workflowIds = new Set();
                invocations.map((invocation) => {
                    historyIds.add(invocation.history_id);
                    workflowIds.add(invocation.workflow_id);
                });
                historyIds.forEach((history_id) => this.getHistoryById(history_id) || this.loadHistoryById(history_id));
                workflowIds.forEach(
                    (workflow_id) =>
                        this.getWorkflowByInstanceId(workflow_id) || this.fetchWorkflowForInstanceId(workflow_id)
                );
            }
        },
    },
    methods: {
        ...mapCacheActions(["fetchWorkflowForInstanceId"]),
        ...mapCacheActions("history", ["loadHistoryById"]),
        async provider(ctx) {
            ctx.root = this.root;
            const extraParams = this.ownerGrid ? {} : { include_terminal: false };
            if (this.storedWorkflowId) {
                extraParams["workflow_id"] = this.storedWorkflowId;
            }
            if (this.userId) {
                extraParams["user_id"] = this.userId;
            }
            const promise = invocationsProvider(ctx, this.setRows, extraParams).catch(this.onError);
            const invocationItems = await promise;
            this.invocationItems = invocationItems;
            return invocationItems;
        },
        swapRowDetails(row) {
            row.toggleDetails();
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

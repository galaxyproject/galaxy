<template>
    <div>
        <div v-if="error" class="alert alert-danger" show>{{ error }}</div>
        <div v-else>
            <span v-if="loading">
                <span class="fa fa-spinner fa-spin" />
                Loading workflows...
            </span>
            <div v-else>
                <b-alert :variant="messageVariant" :show="showMessage">{{ message }}</b-alert>
                <b-row class="mb-3">
                    <b-col cols="6">
                        <b-input
                            class="m-1"
                            name="query"
                            placeholder="search workflows"
                            autocomplete="off"
                            type="text"
                            v-model="filter"
                        />
                    </b-col>
                    <b-col>
                        <span class="float-right">
                            <b-button class="m-1" @click="createWorkflow">
                                <span class="fa fa-plus" />
                                Create
                            </b-button>
                            <b-button class="m-1" @click="importWorkflow">
                                <span class="fa fa-upload" />
                                Import
                            </b-button>
                        </span>
                    </b-col>
                </b-row>
                <b-table striped :fields="fields" :items="workflows" :filter="filter" @filtered="filtered">
                    <template slot="name" slot-scope="row">
                        <workflowdropdown
                            :workflow="row.item"
                            @onAdd="onAdd"
                            @onRemove="onRemove"
                            @onUpdate="onUpdate"
                            @onSuccess="onSuccess"
                            @onError="onError"
                        />
                    </template>
                    <template slot="create_time" slot-scope="data">
                        <span class="text-nowrap">{{ data.value }}</span>
                    </template>
                    <template slot="bookmark" slot-scope="row">
                        <b-form-checkbox v-model="row.item.show_in_tool_panel" @change="bookmarkWorkflow(row.item)" />
                    </template>
                    <template slot="execute" slot-scope="row">
                        <b-button class="btn-sm btn-primary fa fa-play" @click.stop="executeWorkflow(row.item)" />
                    </template>
                </b-table>
                <div v-if="showNotFound">
                    No matching entries found for: <span class="font-weight-bold">{{ this.filter }}</span
                    >.
                </div>
                <div v-if="showNotAvailable">
                    No workflows found. You may create or import new workflows.
                </div>
            </div>
        </div>
    </div>
</template>
<script>
import { getAppRoot } from "onload/loadConfig";
import { Services } from "./services.js";
import WorkflowDropdown from "./WorkflowDropdown.vue";

export default {
    components: {
        workflowdropdown: WorkflowDropdown
    },
    data() {
        return {
            error: null,
            fields: {
                name: {
                    sortable: true
                },
                description: {
                    sortable: true
                },
                create_time: {
                    label: "Created",
                    sortable: true
                },
                bookmark: {},
                execute: {
                    label: "",
                    sortable: false
                }
            },
            filter: "",
            loading: true,
            message: null,
            messageVariant: null,
            nWorkflows: 0,
            workflows: []
        };
    },
    computed: {
        showNotFound() {
            return this.nWorkflows === 0 && this.filter;
        },
        showNotAvailable() {
            return this.nWorkflows === 0 && !this.filter;
        },
        showMessage() {
            return !!this.message;
        }
    },
    created() {
        this.root = getAppRoot();
        this.services = new Services({ root: this.root });
        this.load();
    },
    methods: {
        load() {
            this.loading = true;
            this.filter = "";
            this.services
                .getWorkflows()
                .then(workflows => {
                    this.workflows = workflows;
                    this.nWorkflows = workflows.length;
                    this.loading = false;
                })
                .catch(error => {
                    this.error = error;
                });
        },
        filtered: function(items) {
            this.nWorkflows = items.length;
        },
        createWorkflow: function(workflow) {
            window.location = `${this.root}workflows/create`;
        },
        importWorkflow: function(workflow) {
            window.location = `${this.root}workflows/import`;
        },
        executeWorkflow: function(workflow) {
            window.location = `${this.root}workflows/run?id=${workflow.id}`;
        },
        bookmarkWorkflow: function(workflow) {
            // This reloads the whole page, so that the workflow appears in the tool panel.
            // Ideally we would notify only the tool panel of a change
            const id = workflow.id;
            const show_in_tool_panel = workflow.show_in_tool_panel;
            const data = { show_in_tool_panel: !show_in_tool_panel };
            this.services
                .updateWorkflow(id, data)
                .then(() => {
                    window.location = `${getAppRoot()}workflows/list`;
                })
                .catch(error => {
                    this.onError(error);
                });
        },
        onAdd: function(workflow) {
            this.workflows.unshift(workflow);
            this.nWorkflows = this.workflows.length;
        },
        onRemove: function(id) {
            this.workflows = this.workflows.filter(item => item.id !== id);
            this.nWorkflows = this.workflows.length;
        },
        onUpdate: function(id, data) {
            let workflow = this.workflows.find(item => item.id === id);
            Object.assign(workflow, data);
            this.workflows = [...this.workflows];
        },
        onSuccess: function(message) {
            this.message = message;
            this.messageVariant = "success";
        },
        onError: function(message) {
            this.message = message;
            this.messageVariant = "danger";
        }
    }
};
</script>

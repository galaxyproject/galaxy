<template>
    <div>
        <div v-if="error" class="alert alert-danger" show>{{ error }}</div>
        <div v-else>
            <span v-if="loading">
                <font-awesome-icon icon="spinner" spin />
                Loading workflows...
            </span>
            <div v-else>
                <b-alert :variant="messageVariant" :show="showMessage">{{ message }}</b-alert>
                <b-row class="mb-3">
                    <b-col cols="6">
                        <b-input
                            id="workflow-search"
                            class="m-1"
                            name="query"
                            placeholder="Search Workflows"
                            autocomplete="off"
                            type="text"
                            v-model="filter"
                        />
                    </b-col>
                    <b-col>
                        <span class="float-right">
                            <b-button id="workflow-create" class="m-1" @click="createWorkflow">
                                <font-awesome-icon icon="plus" />
                                Create
                            </b-button>
                            <b-button id="workflow-import" class="m-1" @click="importWorkflow">
                                <font-awesome-icon icon="upload" />
                                Import
                            </b-button>
                        </span>
                    </b-col>
                </b-row>
                <b-table
                    id="workflow-table"
                    striped
                    :fields="fields"
                    :items="workflows"
                    :filter="filter"
                    @filtered="filtered"
                >
                    <template v-slot:cell(name)="row">
                        <WorkflowDropdown
                            :workflow="row.item"
                            @onAdd="onAdd"
                            @onRemove="onRemove"
                            @onUpdate="onUpdate"
                            @onSuccess="onSuccess"
                            @onError="onError"
                        />
                    </template>
                    <template v-slot:cell(tags)="row">
                        <Tags :index="row.index" :tags="row.item.tags" @input="onTags" />
                    </template>
                    <template v-slot:cell(bookmark)="row">
                        <b-form-checkbox v-model="row.item.show_in_tool_panel" @change="bookmarkWorkflow(row.item)" />
                    </template>
                    <template v-slot:cell(create_time)="data">
                        <UtcDate :date="data.value" mode="elapsed" />
                    </template>
                    <template v-slot:cell(execute)="row">
                        <b-button
                            v-b-tooltip.hover.bottom
                            title="Run Workflow"
                            class="workflow-run btn-sm btn-primary fa fa-play"
                            @click.stop="executeWorkflow(row.item)"
                        />
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
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faPlus } from "@fortawesome/free-solid-svg-icons";
import { faSpinner } from "@fortawesome/free-solid-svg-icons";
import { faUpload } from "@fortawesome/free-solid-svg-icons";

import { getAppRoot } from "onload/loadConfig";
import { Services } from "./services";
import Tags from "components/Common/Tags";
import WorkflowDropdown from "./WorkflowDropdown";
import UtcDate from "components/UtcDate";

library.add(faPlus);
library.add(faUpload);
library.add(faSpinner);

export default {
    components: {
        FontAwesomeIcon,
        UtcDate,
        Tags,
        WorkflowDropdown,
    },
    data() {
        return {
            error: null,
            fields: [
                {
                    key: "name",
                    sortable: true,
                },
                {
                    key: "tags",
                    sortable: true,
                },
                {
                    label: "Created",
                    key: "create_time",
                    sortable: true,
                },
                {
                    key: "bookmark",
                },
                {
                    key: "execute",
                    label: "",
                },
            ],
            filter: "",
            loading: true,
            message: null,
            messageVariant: null,
            nWorkflows: 0,
            workflows: [],
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
        },
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
                .then((workflows) => {
                    this.workflows = workflows;
                    this.nWorkflows = workflows.length;
                    this.loading = false;
                })
                .catch((error) => {
                    this.error = error;
                });
        },
        filtered: function (items) {
            this.nWorkflows = items.length;
        },
        createWorkflow: function (workflow) {
            window.location = `${this.root}workflows/create`;
        },
        importWorkflow: function (workflow) {
            window.location = `${this.root}workflows/import`;
        },
        executeWorkflow: function (workflow) {
            window.location = `${this.root}workflows/run?id=${workflow.id}`;
        },
        bookmarkWorkflow: function (workflow) {
            // This reloads the whole page, so that the workflow appears in the tool panel.
            // Ideally we would notify only the tool panel of a change
            const id = workflow.id;
            const show_in_tool_panel = workflow.show_in_tool_panel;
            const tags = workflow.tags;
            const data = {
                show_in_tool_panel: !show_in_tool_panel,
                tags: tags,
            };
            this.services
                .updateWorkflow(id, data)
                .then(() => {
                    window.location = `${getAppRoot()}workflows/list`;
                })
                .catch((error) => {
                    this.onError(error);
                });
        },
        onTags: function (tags, index) {
            const workflow = this.workflows[index];
            workflow.tags = tags;
            this.services
                .updateWorkflow(workflow.id, {
                    show_in_tool_panel: workflow.show_in_tool_panel,
                    tags: workflow.tags,
                })
                .catch((error) => {
                    this.onError(error);
                });
        },
        onAdd: function (workflow) {
            this.workflows.unshift(workflow);
            this.nWorkflows = this.workflows.length;
        },
        onRemove: function (id) {
            this.workflows = this.workflows.filter((item) => item.id !== id);
            this.nWorkflows = this.workflows.length;
        },
        onUpdate: function (id, data) {
            const workflow = this.workflows.find((item) => item.id === id);
            Object.assign(workflow, data);
            this.workflows = [...this.workflows];
        },
        onSuccess: function (message) {
            this.message = message;
            this.messageVariant = "success";
        },
        onError: function (message) {
            this.message = message;
            this.messageVariant = "danger";
        },
    },
};
</script>

<template>
    <div>
        <div v-if="error" class="alert alert-danger" show>{{ error }}</div>
        <div v-else>
            <loading-span v-if="loading" message="Loading workflows" />
            <div v-else>
                <b-alert :variant="messageVariant" :show="showMessage">{{ message }}</b-alert>
                <b-row class="mb-3">
                    <b-col cols="6">
                        <b-input
                            id="workflow-search"
                            class="m-1"
                            name="query"
                            :placeholder="titleSearchWorkflows"
                            autocomplete="off"
                            type="text"
                            v-model="filter" />
                    </b-col>
                    <b-col>
                        <span class="float-right">
                            <b-button id="workflow-create" class="m-1" @click="createWorkflow">
                                <font-awesome-icon icon="plus" />
                                {{ titleCreate }}
                            </b-button>
                            <b-button id="workflow-import" class="m-1" @click="importWorkflow">
                                <font-awesome-icon icon="upload" />
                                {{ titleImport }}
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
                    @filtered="filtered">
                    <template v-slot:cell(name)="row">
                        <WorkflowDropdown
                            :workflow="row.item"
                            @onAdd="onAdd"
                            @onRemove="onRemove"
                            @onUpdate="onUpdate"
                            @onSuccess="onSuccess"
                            @onError="onError" />
                    </template>
                    <template v-slot:cell(tags)="row">
                        <Tags :index="row.index" :tags="row.item.tags" @input="onTags" />
                    </template>
                    <template v-slot:cell(published)="row">
                        <font-awesome-icon v-if="row.item.published" v-b-tooltip.hover title="Published" icon="globe" />
                        <font-awesome-icon v-if="row.item.shared" v-b-tooltip.hover title="Shared" icon="share-alt" />
                    </template>
                    <template v-slot:cell(show_in_tool_panel)="row">
                        <b-link @click="bookmarkWorkflow(row.item, false)" v-if="row.item.show_in_tool_panel">
                            <font-awesome-icon :icon="['fas', 'star']" />
                        </b-link>
                        <b-link @click="bookmarkWorkflow(row.item, true)" v-else>
                            <font-awesome-icon :icon="['far', 'star']" />
                        </b-link>
                    </template>
                    <template v-slot:cell(update_time)="data">
                        <UtcDate :date="data.value" mode="elapsed" />
                    </template>
                    <template v-slot:cell(execute)="row">
                        <b-button
                            v-b-tooltip.hover.bottom
                            :title="titleRunWorkflow"
                            class="workflow-run btn-sm btn-primary fa fa-play"
                            @click.stop="executeWorkflow(row.item)" />
                    </template>
                </b-table>
                <div v-if="showNotFound">
                    No matching entries found for: <span class="font-weight-bold">{{ this.filter }}</span
                    >.
                </div>
                <div v-if="showNotAvailable">No workflows found. You may create or import new workflows.</div>
            </div>
        </div>
    </div>
</template>
<script>
import _l from "utils/localization";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faPlus, faShareAlt, faGlobe, faUpload, faSpinner, faStar } from "@fortawesome/free-solid-svg-icons";
import { faStar as farStar } from "@fortawesome/free-regular-svg-icons";
import { getAppRoot } from "onload/loadConfig";
import { Services } from "./services";
import Tags from "components/Common/Tags";
import WorkflowDropdown from "./WorkflowDropdown";
import LoadingSpan from "components/LoadingSpan";
import UtcDate from "components/UtcDate";
import { getGalaxyInstance } from "app";

library.add(faPlus, faUpload, faSpinner, faGlobe, faShareAlt, farStar, faStar);

export default {
    components: {
        FontAwesomeIcon,
        LoadingSpan,
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
                    label: _l("Name"),
                    sortable: true,
                },
                {
                    key: "tags",
                    label: _l("Tags"),
                    sortable: true,
                },
                {
                    label: _l("Updated"),
                    key: "update_time",
                    sortable: true,
                },
                {
                    label: _l("Sharing"),
                    key: "published",
                    sortable: true,
                },
                {
                    label: _l("Bookmarked"),
                    key: "show_in_tool_panel",
                    sortable: true,
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
            titleSearchWorkflows: _l("Search Workflows"),
            titleCreate: _l("Create"),
            titleImport: _l("Import"),
            titleRunWorkflow: _l("Run workflow"),
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
        bookmarkWorkflow: function (workflow, checked) {
            const id = workflow.id;
            const tags = workflow.tags;
            const data = {
                show_in_tool_panel: checked,
                tags: tags,
            };
            this.services
                .updateWorkflow(id, data)
                .then(({ id, name }) => {
                    if (checked) {
                        getGalaxyInstance().config.stored_workflow_menu_entries.push({ id: id, name: name });
                    } else {
                        const indexToRemove = getGalaxyInstance().config.stored_workflow_menu_entries.findIndex(
                            (workflow) => workflow.id === id
                        );
                        getGalaxyInstance().config.stored_workflow_menu_entries.splice(indexToRemove, 1);
                    }

                    this.workflows.find((workflow) => {
                        if (workflow.id === id) {
                            workflow.show_in_tool_panel = checked;
                            return true;
                        }
                    });
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

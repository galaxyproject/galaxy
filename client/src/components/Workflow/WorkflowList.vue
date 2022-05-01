<template>
    <div>
        <div v-if="error" class="alert alert-danger" show>{{ error }}</div>
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
                :id="tableId"
                :fields="fields"
                :items="provider"
                v-model="workflowItemsModel"
                :per-page="perPage"
                :current-page="currentPage"
                hover
                striped
                caption-top
                fixed
                show-empty>
                <template v-slot:empty>
                    <loading-span v-if="loading" message="Loading workflows" />
                    <b-alert v-else id="no-workflows" variant="info" show>
                        <div v-if="showNotFound">
                            No matching entries found for: <span class="font-weight-bold">{{ filter }}</span
                            >.
                        </div>
                        <div v-if="showNotAvailable">No workflows found. You may create or import new workflows.</div>
                    </b-alert>
                </template>
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
                    <Tags :index="row.index" :tags="row.item.tags" @input="onTags" @tag-click="onTagClick" />
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
            <b-pagination
                v-model="currentPage"
                v-show="rows >= perPage"
                class="gx-workflows-grid-pager"
                v-bind="paginationAttrs"></b-pagination>
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
import { storedWorkflowsProvider } from "components/providers/StoredWorkflowsProvider";
import Tags from "components/Common/Tags";
import WorkflowDropdown from "./WorkflowDropdown";
import UtcDate from "components/UtcDate";
import { getGalaxyInstance } from "app";
import paginationMixin from "./paginationMixin";

library.add(faPlus, faUpload, faSpinner, faGlobe, faShareAlt, farStar, faStar);

export default {
    components: {
        FontAwesomeIcon,
        UtcDate,
        Tags,
        WorkflowDropdown,
    },
    mixins: [paginationMixin],
    data() {
        return {
            tableId: "workflow-table",
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
                    sortable: false,
                },
                {
                    label: _l("Updated"),
                    key: "update_time",
                    sortable: true,
                },
                {
                    label: _l("Sharing"),
                    key: "published",
                    sortable: false,
                },
                {
                    label: _l("Bookmarked"),
                    key: "show_in_tool_panel",
                    sortable: false,
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
            titleSearchWorkflows: _l("Search Workflows"),
            titleCreate: _l("Create"),
            titleImport: _l("Import"),
            titleRunWorkflow: _l("Run workflow"),
            workflowItemsModel: [],
            workflowItems: [],
            perPage: this.rowsPerPage(50),
        };
    },
    computed: {
        showNotFound() {
            return this.filter;
        },
        showNotAvailable() {
            return !this.filter;
        },
        showMessage() {
            return !!this.message;
        },
        apiUrl() {
            return `${getAppRoot()}api/workflows`;
        },
    },
    created() {
        this.root = getAppRoot();
        this.services = new Services({ root: this.root });
    },
    watch: {
        filter(val) {
            this.refresh();
        },
    },
    methods: {
        async provider(ctx) {
            ctx.apiUrl = this.apiUrl;
            const extraParams = { search: this.filter, skip_step_counts: true };
            this.workflowItems = await storedWorkflowsProvider(ctx, this.setRows, extraParams);
            return this.workflowItems;
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

                    this.workflowItems.find((workflow) => {
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
            const workflow = this.workflowItemsModel[index];
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
        onTagClick: function (tag) {
            const tagFilter = `tag:'${tag.text}'`;
            const initialFilter = this.filter;
            if (initialFilter.length === 0) {
                this.filter = tagFilter;
            } else if (initialFilter.indexOf(tagFilter) < 0) {
                this.filter = `${tagFilter} ${initialFilter}`;
            }
        },
        onAdd: function (workflow) {
            if (this.currentPage == 1) {
                this.refresh();
            } else {
                this.currentPage = 1;
            }
        },
        onRemove: function (id) {
            this.refresh();
        },
        onUpdate: function (id, data) {
            this.refresh();
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

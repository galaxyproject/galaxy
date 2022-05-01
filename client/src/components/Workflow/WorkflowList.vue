<template>
    <div>
        <b-alert class="index-grid-message" :variant="messageVariant" :show="showMessage">{{ message }}</b-alert>
        <b-row class="mb-3">
            <b-col cols="6">
                <index-filter
                    id="workflow-search"
                    :placeholder="titleSearchWorkflows"
                    :help-html="helpHtml"
                    v-model="filter">
                </index-filter>
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
                <font-awesome-icon
                    v-if="row.item.published"
                    v-b-tooltip.hover
                    title="Published"
                    icon="globe"
                    @click="appendFilter('is:published')" />
                <font-awesome-icon
                    v-if="row.item.shared"
                    v-b-tooltip.hover
                    title="Shared"
                    icon="share-alt"
                    @click="appendFilter('is:shared_with_me')" />
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
import IndexFilter from "./IndexFilter";

library.add(faPlus, faUpload, faSpinner, faGlobe, faShareAlt, farStar, faStar);

const helpHtml = `<div>
<p>This textbox box can be used to filter the workflows displayed.

<p>Text entered here will be searched against workflow names and tags. Additionally, advanced
filtering tags can be used to refine the search more precisely. Tags are of the form
<code>&lt;tag_name&gt;:&lt;tag_value&gt;</code> or <code>&lt;tag_name&gt;:'&lt;tag_value&gt;'</code>.
For instance to search just for RNAseq in the workflow name, <code>name:rnsseq</code> can be used.
Notice by default the search is not case-sensitive.

If the quoted version of tag is used, the search is not case sensitive and only full matches will be
returned. So <code>name:'RNAseq'</code> would show only workflows named exactly <code>RNAseq</code>.

<p>The available tags are:
<dl>
    <dt><code>name</code></dt>
    <dd>This filters only against the workflow name.</dd>
    <dt><code>tag</code></dt>
    <dd>This filters only against the workflow tag. You may also just click on a tag in your list of workflows to filter on that tag using this directly.</dd>
    <dt><code>is:published</code></dt>
    <dd>This filters the workflows such that only published workflows are shown. You may also just click on the "published" icon of a worklfow in your list to filter on this directly.</dd>
    <dt><code>is:shared</code></dt>
    <dd>This filters the workflows such that only workflows shared from another user directly with you are are shown. You may also just click on the "shared with me" icon of a worklfow in your list to filter on this directly.</dd>
</dl>
</div>
`;

export default {
    components: {
        FontAwesomeIcon,
        UtcDate,
        Tags,
        WorkflowDropdown,
        IndexFilter,
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
            titleSearchWorkflows: _l("Search Workflows"),
            titleCreate: _l("Create"),
            titleImport: _l("Import"),
            titleRunWorkflow: _l("Run workflow"),
            workflowItemsModel: [],
            workflowItems: [],
            helpHtml: helpHtml,
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
            ctx.root = this.root;
            const extraParams = { search: this.filter, skip_step_counts: true };
            const promise = storedWorkflowsProvider(ctx, this.setRows, extraParams).catch(this.onError);
            this.workflowItems = await promise;
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
        filterPublished() {
            this.appendFilter("is:published");
        },
        onTagClick: function (tag) {
            const tagFilter = `tag:'${tag.text}'`;
            this.appendFilter(tagFilter);
        },
        appendFilter(text) {
            const initialFilter = this.filter;
            if (initialFilter.length === 0) {
                this.filter = text;
            } else if (initialFilter.indexOf(text) < 0) {
                this.filter = `${text} ${initialFilter}`;
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
    },
};
</script>

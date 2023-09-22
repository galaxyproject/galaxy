<template>
    <div class="workflows-list" aria-labelledby="workflows-title">
        <h1 id="workflows-title" class="mb-3 h-lg">
            {{ title }}
        </h1>
        <b-alert class="index-grid-message" :variant="messageVariant" :show="showMessage">{{ message }}</b-alert>
        <b-alert class="index-grid-message" dismissible :variant="importStatus" :show="Boolean(importMessage)">
            {{ importMessage }}
        </b-alert>
        <b-row class="mb-3">
            <b-col cols="6" class="m-1">
                <IndexFilter v-bind="filterAttrs" id="workflow-search" v-model="filter" />
            </b-col>
            <b-col>
                <WorkflowIndexActions :root="root" class="float-right"></WorkflowIndexActions>
            </b-col>
        </b-row>
        <b-table v-model="workflowItemsModel" v-bind="{ ...defaultTableAttrs, ...indexTableAttrs }">
            <template v-slot:empty>
                <loading-span v-if="loading" message="Loading workflows" />
                <b-alert v-else id="no-workflows" variant="info" show>
                    <div v-if="isFiltered">
                        No matching entries found for: <span class="font-weight-bold">{{ filter }}</span
                        >.
                    </div>
                    <div v-else>No workflows found. You may create or import new workflows.</div>
                </b-alert>
            </template>
            <template v-slot:cell(name)="row">
                <WorkflowDropdown
                    :workflow="row.item"
                    :details-showing="row.detailsShowing"
                    @onAdd="onAdd"
                    @onRemove="onRemove"
                    @onUpdate="onUpdate"
                    @onSuccess="onSuccess"
                    @onError="onError"
                    @onRestore="onRestore"
                    @toggleDetails="row.toggleDetails" />
            </template>
            <template v-slot:cell(tags)="row">
                <StatelessTags
                    clickable
                    :value="row.item.tags"
                    :disabled="row.item.deleted || published"
                    @input="(tags) => onTags(tags, row.index)"
                    @tag-click="onTagClick" />
            </template>
            <template v-slot:cell(published)="row">
                <SharingIndicators
                    v-if="!row.item.deleted"
                    :object="row.item"
                    @filter="(filter) => appendFilter(filter, true)" />
                <div v-else>&#8212;</div>
            </template>
            <template v-slot:cell(show_in_tool_panel)="row">
                <WorkflowBookmark
                    v-if="!row.item.deleted"
                    :checked="row.item.show_in_tool_panel"
                    @bookmark="(checked) => bookmarkWorkflow(row.item.id, checked)" />
                <div v-else>&#8212;</div>
            </template>
            <template v-slot:cell(update_time)="data">
                <UtcDate :date="data.value" mode="elapsed" />
            </template>
            <template v-slot:cell(owner)="data">
                <a class="workflow-filter-link-owner" href="#" @click="appendTagFilter('user', data.value)">{{
                    data.value
                }}</a>
            </template>
            <template v-slot:cell(execute)="row">
                <WorkflowRunButton v-if="!row.item.deleted" :id="row.item.id" :root="root" />
                <div v-else>&#8212;</div>
            </template>
            <template v-slot:row-details="data">
                <b-card>
                    <p class="workflow-dropdown-description">{{ data.item.description }}</p>
                </b-card>
            </template>
        </b-table>
        <b-pagination
            v-show="rows >= perPage"
            v-model="currentPage"
            class="gx-workflows-grid-pager"
            v-bind="paginationAttrs"></b-pagination>
    </div>
</template>
<script>
import _l from "utils/localization";
import { Services } from "./services";
import { getAppRoot } from "onload/loadConfig";
import { storedWorkflowsProvider } from "components/providers/StoredWorkflowsProvider";
import StatelessTags from "@/components/TagsMultiselect/StatelessTags.vue";
import WorkflowDropdown from "./WorkflowDropdown";
import UtcDate from "components/UtcDate";
import { getGalaxyInstance } from "app";
import paginationMixin from "./paginationMixin";
import filtersMixin from "components/Indices/filtersMixin";
import WorkflowIndexActions from "./WorkflowIndexActions";
import WorkflowBookmark from "./WorkflowBookmark";
import WorkflowRunButton from "./WorkflowRunButton.vue";
import SharingIndicators from "components/Indices/SharingIndicators";

const helpHtml = `<div>
    <p>This input can be used to filter the workflows displayed.</p>

    <p>
        Text entered here will be searched against workflow names and workflow
        tags. Additionally, advanced filtering tags can be used to refine the
        search more precisely. Filtering tags are of the form
        <code>&lt;tag_name&gt;:&lt;tag_value&gt;</code> or
        <code>&lt;tag_name&gt;:'&lt;tag_value&gt;'</code>. For instance to
        search just for RNAseq in the workflow name,
        <code>name:rnsseq</code> can be used. Notice by default the search is
        not case-sensitive. If the quoted version of tag is used, the search is
        case sensitive and only full matches will be returned. So
        <code>name:'RNAseq'</code> would show only workflows named exactly
        <code>RNAseq</code>.
    </p>

    <p>The available filtering tags are:</p>
    <dl>
        <dt><code>name</code></dt>
        <dd>
            Shows workflows with the given sequence of characters in their names.
        </dd>
        <dt><code>tag</code></dt>
        <dd>
            Shows workflows with the given workflow tag. You may also click
            on a tag to filter on that tag directly.
        </dd>
        <dt><code>is:published</code></dt>
        <dd>
            Shows published workflows.
        </dd>
        <dt><code>is:importable</code></dt>
        <dd>
            Shows importable workflows (this also means they have URL generated).
        </dd>
        <dt><code>is:shared_with_me</code></dt>
        <dd>
            Shows workflows shared by another user directly with you.
        </dd>
        <dt><code>is:deleted</code></dt>
        <dd>Shows deleted workflows.</dd>
    </dl>
</div>`;

const NAME_FIELD = { key: "name", label: _l("Name"), sortable: true };
const TAGS_FIELD = { key: "tags", label: _l("Tags"), sortable: false, thStyle: { width: "20%" } };
const UPDATED_FIELD = { label: _l("Updated"), key: "update_time", sortable: true, thStyle: { width: "15%" } };
const SHARING_FIELD = { label: _l("Sharing"), key: "published", sortable: false, thStyle: { width: "10%" } };
const BOOKMARKED_FIELD = {
    label: _l("Bookmarked"),
    key: "show_in_tool_panel",
    sortable: false,
    thStyle: { width: "10%" },
};
const EXECUTE_FIELD = { key: "execute", label: "Run", thStyle: { width: "10%" } };
const OWNER_FIELD = { key: "owner", label: _l("Owner"), sortable: false, thStyle: { width: "15%" } };

const PERSONAL_FIELDS = [NAME_FIELD, TAGS_FIELD, UPDATED_FIELD, SHARING_FIELD, BOOKMARKED_FIELD, EXECUTE_FIELD];
const PUBLISHED_FIELDS = [NAME_FIELD, TAGS_FIELD, UPDATED_FIELD, OWNER_FIELD];

export default {
    components: {
        UtcDate,
        StatelessTags,
        WorkflowDropdown,
        WorkflowBookmark,
        WorkflowIndexActions,
        SharingIndicators,
        WorkflowRunButton,
    },
    mixins: [paginationMixin, filtersMixin],
    props: {
        inputDebounceDelay: {
            type: Number,
            default: 500,
        },
        importMessage: {
            type: String,
            default: null,
        },
        importStatus: {
            type: String,
            default: "success",
        },
        published: {
            // Render the published workflows version of this grid.
            type: Boolean,
            default: false,
        },
        query: {
            type: String,
            required: false,
            default: "",
        },
    },
    data() {
        const fields = this.published ? PUBLISHED_FIELDS : PERSONAL_FIELDS;
        const implicitFilter = this.published ? "is:published" : null;
        return {
            tableId: "workflow-table",
            fields: fields,
            titleSearch: "search workflows",
            workflowItemsModel: [],
            helpHtml: helpHtml,
            perPage: this.rowsPerPage(this.defaultPerPage || 20),
            dataProvider: storedWorkflowsProvider,
            implicitFilter: implicitFilter,
            defaultTableAttrs: { "sort-by": "update_time", "sort-desc": true, "no-sort-reset": "", fields: fields },
        };
    },
    computed: {
        dataProviderParameters() {
            const extraParams = { search: this.normalizeTag(this.effectiveFilter), skip_step_counts: true };
            if (this.published) {
                extraParams.show_published = true;
                extraParams.show_shared = false;
            }
            return extraParams;
        },
        title() {
            return this.published ? `Published Workflows` : `Workflows`;
        },
    },
    watch: {
        filter(val) {
            this.refresh();
        },
    },
    created() {
        this.root = getAppRoot();
        this.services = new Services();
        if (this.query) {
            this.filter = this.query;
        }
    },
    methods: {
        decorateData(item) {
            this.services._addAttributes(item);
        },
        bookmarkWorkflow: function (id, checked) {
            const data = {
                show_in_tool_panel: checked,
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

                    this.items.find((workflow) => {
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
                    tags: workflow.tags,
                })
                .catch((error) => {
                    this.onError(error);
                });
            this.$emit("input", workflow.tags);
        },
        onTagClick: function (tag) {
            this.appendTagFilter("tag", tag);
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
        onRestore: function (id) {
            this.refresh();
        },
        normalizeTag: function (tag) {
            return tag.replace(/(tag:')#/g, "$1name:");
        },
    },
};
</script>

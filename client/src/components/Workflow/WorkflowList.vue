<template>
    <div>
        <b-alert class="index-grid-message" :variant="messageVariant" :show="showMessage">{{ message }}</b-alert>
        <b-alert class="index-grid-message" dismissible :variant="importStatus" :show="Boolean(importMessage)">
            {{ importMessage }}
        </b-alert>
        <b-row class="mb-3">
            <b-col cols="6" class="m-1">
                <index-filter
                    id="workflow-search"
                    v-model="filter"
                    :debounce-delay="inputDebounceDelay"
                    :placeholder="titleSearch"
                    :help-html="helpHtml">
                </index-filter>
            </b-col>
            <b-col>
                <WorkflowIndexActions :root="root" class="float-right"> </WorkflowIndexActions>
            </b-col>
        </b-row>
        <b-table v-model="workflowItemsModel" :fields="fields" :items="provider" v-bind="indexTableAttrs">
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
                    @onAdd="onAdd"
                    @onRemove="onRemove"
                    @onUpdate="onUpdate"
                    @onSuccess="onSuccess"
                    @onError="onError"
                    @onRestore="onRestore" />
            </template>
            <template v-slot:cell(tags)="row">
                <Tags
                    :index="row.index"
                    :tags="row.item.tags"
                    :disabled="row.item.deleted"
                    @input="onTags"
                    @tag-click="onTagClick" />
            </template>
            <template v-slot:cell(published)="row">
                <SharingIndicators
                    v-if="!row.item.deleted"
                    :object="row.item"
                    @filter="(filter) => appendFilter(filter)" />
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
            <template v-slot:cell(execute)="row">
                <WorkflowRunButton v-if="!row.item.deleted" :id="row.item.id" :root="root" />
                <div v-else>&#8212;</div>
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
import Tags from "components/Common/Tags";
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
            Shows workflows with given sequence of characters in their names.
        </dd>
        <dt><code>tag</code></dt>
        <dd>
            Shows workflows with the given workflow tag. You may also just click
            on a tag in your list of workflows to filter on that tag directly.
        </dd>
        <dt><code>is:published</code></dt>
        <dd>
            Shows published workflows. You may also just click on the
            "published" icon of a workflow in your list to filter on this
            directly.
        </dd>
        <dt><code>is:shared</code></dt>
        <dd>
            Shows workflows shared by another user directly with you. You may
            also just click on the "shared with me" icon of a workflow in your
            list to filter on this directly.
        </dd>
        <dt><code>is:deleted</code></dt>
        <dd>Shows deleted workflows.</dd>
    </dl>
</div>`;

export default {
    components: {
        UtcDate,
        Tags,
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
    },
    data() {
        return {
            tableId: "workflow-table",
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
            titleSearch: _l("Search Workflows"),
            workflowItemsModel: [],
            workflowItems: [],
            helpHtml: helpHtml,
            perPage: this.rowsPerPage(50),
        };
    },
    watch: {
        filter(val) {
            this.refresh();
        },
    },
    created() {
        this.root = getAppRoot();
        this.services = new Services();
    },
    methods: {
        async provider(ctx) {
            ctx.root = this.root;
            const extraParams = { search: this.filter, skip_step_counts: true };
            const promise = storedWorkflowsProvider(ctx, this.setRows, extraParams).catch(this.onError);
            const workflowItems = await promise;
            (workflowItems || []).forEach((item) => this.services._addAttributes(item));
            this.workflowItems = workflowItems;
            return this.workflowItems;
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
                    tags: workflow.tags,
                })
                .catch((error) => {
                    this.onError(error);
                });
        },
        onTagClick: function (tag) {
            this.appendTagFilter("tag", tag.text);
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
    },
};
</script>

<template>
    <div>
        <b-alert v-bind="alertAttrs">{{ message }}</b-alert>
        <b-row class="mb-3">
            <b-col cols="6">
                <index-filter v-bind="filterAttrs" id="page-search" v-model="filter"> </index-filter>
            </b-col>
            <b-col>
                <PageIndexActions :root="root" class="float-right" />
            </b-col>
        </b-row>
        <b-table v-model="itemsModel" :fields="fields" v-bind="indexTableAttrs">
            <template v-slot:empty>
                <loading-span v-if="loading" message="Loading pages" />
                <b-alert v-else id="no-pages" variant="info" show>
                    <div v-if="isFiltered">
                        No matching entries found for: <span class="font-weight-bold">{{ filter }}</span
                        >.
                    </div>
                    <div v-else>No pages found. You may create a new page.</div>
                </b-alert>
            </template>
            <template v-slot:cell(title)="row">
                <PageDropdown
                    :page="row.item"
                    :root="root"
                    @onAdd="onAdd"
                    @onRemove="onRemove"
                    @onUpdate="onUpdate"
                    @onSuccess="onSuccess"
                    @onError="onError" />
            </template>
            <template v-slot:cell(tags)="row">
                <Tags
                    :index="row.index"
                    :tags="row.item.tags"
                    :disabled="published"
                    @input="onTags"
                    @tag-click="onTagClick" />
            </template>
            <template v-slot:cell(published)="row">
                <SharingIndicators :object="row.item" @filter="(filter) => appendFilter(filter)" />
            </template>
            <template v-slot:cell(url)="row">
                <PageUrl
                    :root="root"
                    :owner="row.item.username"
                    :slug="row.item.slug"
                    @clickOwner="(username) => appendTagFilter('user', username)" />
            </template>
            <template v-slot:cell(update_time)="data">
                <UtcDate :date="data.value" mode="elapsed" />
            </template>
        </b-table>
        <b-pagination
            v-if="rows >= perPage"
            v-model="currentPage"
            class="gx-pages-grid-pager"
            v-bind="paginationAttrs"></b-pagination>
    </div>
</template>
<script>
import _l from "utils/localization";
import { getAppRoot } from "onload/loadConfig";
// import { Services } from "./services";
import { pagesProvider } from "components/providers/PageProvider";
import Tags from "components/Common/Tags";
import PageDropdown from "./PageDropdown";
import UtcDate from "components/UtcDate";
import paginationMixin from "components/Workflow/paginationMixin";
import filtersMixin from "components/Indices/filtersMixin";
import PageIndexActions from "./PageIndexActions";
import PageUrl from "./PageUrl";

import SharingIndicators from "components/Indices/SharingIndicators";

const helpHtml = `<div>
<p>This textbox can be used to filter the pages displayed.

<p>Text entered here will be searched against page names and tags. Additionally, advanced
filtering tags can be used to refine the search more precisely. Tags are of the form
<code>&lt;tag_name&gt;:&lt;tag_value&gt;</code> or <code>&lt;tag_name&gt;:'&lt;tag_value&gt;'</code>.
For instance to search just for RNAseq in the page name, <code>name:rnaseq</code> can be used.
Notice by default the search is not case-sensitive.

If the quoted version of tag is used, the search is not case sensitive and only full matches will be
returned. So <code>name:'RNAseq'</code> would show only pages named exactly <code>RNAseq</code>.

<p>The available tags are:
<dl>
    <dt><code>title</code></dt>
    <dd>This filters only against the page title.</dd>
    <dt><code>tag</code></dt>
    <dd>This filters only against the page tag. You may also just click on a tag in your list of pages to filter on that tag using this directly.</dd>
    <dt><code>is:published</code></dt>
    <dd>This filters the pages such that only published ones are shown. You may also just click on the "published" icon of a page in your list to filter on this directly.</dd>
    <dt><code>is:shared</code></dt>
    <dd>This filters the pages such that only ones shared from another user directly with you are are shown. You may also just click on the "shared with me" icon of a page in your list to filter on this directly.</dd>
</dl>
</div>
`;

const TITLE_FIELD = { key: "title", label: _l("Title"), sortable: true };
const TAGS_FIELD = { key: "tags", label: _l("Tags"), sortable: false };
const URL_FIELD = { key: "url", label: _l("Public URL"), sortable: false };
const UPDATED_FIELD = { label: _l("Updated"), key: "update_time", sortable: true };
const SHARING_FIELD = { label: _l("Sharing"), key: "published", sortable: false };
// const OWNER_FIELD = { key: "owner", label: _l("Owner"), sortable: true };

const PERSONAL_FIELDS = [TITLE_FIELD, URL_FIELD, TAGS_FIELD, UPDATED_FIELD, SHARING_FIELD];
const PUBLISHED_FIELDS = [TITLE_FIELD, URL_FIELD, TAGS_FIELD, UPDATED_FIELD];

export default {
    components: {
        UtcDate,
        Tags,
        PageIndexActions,
        SharingIndicators,
        PageDropdown,
        PageUrl,
    },
    mixins: [paginationMixin, filtersMixin],
    props: {
        published: {
            // Render the published pages version of this grid.
            type: Boolean,
            default: true,
        },
    },
    data() {
        const fields = this.published ? PUBLISHED_FIELDS : PERSONAL_FIELDS;
        const implicitFilter = this.published ? "is:published" : null;
        return {
            tableId: "page-table",
            fields: fields,
            titleSearch: _l("Search Pages"),
            itemsModel: [],
            items: [],
            helpHtml: helpHtml,
            perPage: this.rowsPerPage(this.defaultPerPage || 50),
            dataProvider: pagesProvider,
            implicitFilter: implicitFilter,
        };
    },
    computed: {
        dataProviderParameters() {
            const extraParams = { search: this.effectiveFilter };
            if (this.published) {
                extraParams.show_published = true;
                extraParams.show_shared = false;
            }
            return extraParams;
        },
    },
    watch: {
        filter(val) {
            this.refresh();
        },
    },
    created() {
        this.root = getAppRoot();
        // this.services = new Services({ root: this.root });
    },
    methods: {
        onTags: function (tags, index) {
            const workflow = this.itemsModel[index];
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
    },
};
</script>

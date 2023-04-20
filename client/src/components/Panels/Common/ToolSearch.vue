<template>
    <div>
        <small v-if="showAdvanced">Filter by name:</small>
        <DelayedInput
            :class="!showAdvanced && 'mb-3'"
            :query="query"
            :delay="100"
            :loading="queryPending"
            :show-advanced="showAdvanced"
            :enable-advanced="enableAdvanced"
            :placeholder="showAdvanced ? 'any name' : placeholder"
            @change="checkQuery"
            @onToggle="onToggle" />
        <div
            v-if="showAdvanced"
            description="advanced tool filters"
            @keyup.enter="onSearch"
            @keyup.esc="onToggle(false)">
            <small class="mt-1">Filter by {{ sectionLabel }}:</small>
            <b-form-input
                v-model="filterSettings['section']"
                autocomplete="off"
                size="sm"
                :placeholder="`any ${sectionLabel}`"
                list="sectionSelect" />
            <b-form-datalist id="sectionSelect" :options="sectionNames"></b-form-datalist>
            <small class="mt-1">Filter by id:</small>
            <b-form-input v-model="filterSettings['id']" size="sm" placeholder="any id" />
            <small class="mt-1">Filter by repository owner:</small>
            <b-form-input v-model="filterSettings['owner']" size="sm" placeholder="any owner" />
            <small class="mt-1">Filter by help text:</small>
            <b-form-input v-model="filterSettings['help']" size="sm" placeholder="any help text" />
            <div class="mt-3">
                <b-button class="mr-1" size="sm" variant="primary" @click="onSearch">
                    <icon icon="search" />
                    <span>{{ "Search" | localize }}</span>
                </b-button>
                <b-button size="sm" @click="onToggle(false)">
                    <icon icon="redo" />
                    <span>{{ "Cancel" | localize }}</span>
                </b-button>
                <b-button title="Search Help" size="sm" @click="showHelp = true">
                    <icon icon="question" />
                </b-button>
                <b-modal v-model="showHelp" title="Tool Advanced Search Help" ok-only>
                    <div>
                        <p>
                            You can use this Advanced Tool Search Panel to find tools by applying search filters, with
                            the results showing up in the center panel.
                        </p>

                        <p>
                            <i>
                                (Clicking on the Section, Repo or Owner labels in the Search Results will activate the
                                according filter)
                            </i>
                        </p>

                        <p>The available tool search filters are:</p>
                        <dl>
                            <dt><code>name</code></dt>
                            <dd>The tool name (stored as tool.name + tool.description in the XML)</dd>
                            <dt><code>section</code></dt>
                            <dd>
                                The tool section is based on the current view you have selected for the panel. <br />
                                When this field is active, you will be able to see a datalist showing the available
                                sections you can filter from. <br />
                                By default, Galaxy tool panel sections are filterable if you are currently on the
                                <i>Full Tool Panel</i> view, and it will show EDAM ontologies or EDAM topics if you have
                                either of those options selected. <br />
                                Change panel views by clicking on the
                                <icon icon="caret-down" />
                                icon at the top right of the tool panel.
                            </dd>
                            <dt><code>id</code></dt>
                            <dd>The tool id (taken from its XML)</dd>
                            <dt><code>owner</code></dt>
                            <dd>
                                For the tools that have been installed from the
                                <a href="https://toolshed.g2.bx.psu.edu/" target="_blank">ToolShed</a>
                                , this <i>owner</i> filter allows you to search for tools from a specific ToolShed
                                repository <b>owner</b>.
                            </dd>
                            <dt><code>help text</code></dt>
                            <dd>
                                This is like a keyword search: you can search for keywords that might exist in a tool's
                                help text. An example input:
                                <i>"genome, RNA, minimap"</i>
                            </dd>
                        </dl>
                    </div>
                </b-modal>
            </div>
        </div>
    </div>
</template>

<script>
import { getGalaxyInstance } from "app";
import DelayedInput from "components/Common/DelayedInput";
import { flattenTools } from "../utilities.js";

export default {
    name: "ToolSearch",
    components: {
        DelayedInput,
    },
    props: {
        currentPanelView: {
            type: String,
            required: true,
        },
        enableAdvanced: {
            type: Boolean,
            default: false,
        },
        placeholder: {
            type: String,
            default: "search tools",
        },
        query: {
            type: String,
            default: null,
        },
        queryPending: {
            type: Boolean,
            default: false,
        },
        showAdvanced: {
            type: Boolean,
            default: false,
        },
        toolbox: {
            type: Array,
            required: true,
        },
    },
    data() {
        return {
            favorites: ["#favs", "#favorites", "#favourites"],
            minQueryLength: 3,
            filterSettings: {},
            showHelp: false,
            searchWorker: null,
        };
    },
    computed: {
        favoritesResults() {
            const Galaxy = getGalaxyInstance();
            return Galaxy.user.getFavorites().tools;
        },
        sectionNames() {
            return this.toolbox.map((section) =>
                section.name !== undefined && section.name !== "Uncategorized" ? section.name : ""
            );
        },
        sectionLabel() {
            return this.currentPanelView === "default" ? "section" : "ontology";
        },
        toolsList() {
            return flattenTools(this.toolbox);
        },
    },
    beforeDestroy() {
        this.searchWorker.terminate();
    },
    mounted() {
        this.searchWorker = new Worker(new URL("../toolSearch.worker.js", import.meta.url));
        this.searchWorker.onmessage = ({ data }) => {
            const { type, payload, query, closestTerm } = data;
            if (type === "searchToolsByKeysResult" && query === this.query) {
                this.$emit("onResults", payload, closestTerm);
            } else if (type === "clearFilterResult") {
                this.$emit("onResults", null);
            } else if (type === "favoriteToolsResult") {
                this.$emit("onResults", this.favoritesResults);
            }
        };
    },
    methods: {
        checkQuery(q) {
            this.filterSettings["name"] = q;
            this.$emit("onQuery", q);
            if (q && q.length >= this.minQueryLength) {
                if (this.favorites.includes(q)) {
                    this.searchWorker.postMessage({ type: "favoriteTools" });
                } else {
                    // keys with sorting order
                    const keys = { exact: 3, name: 2, description: 1, combined: 0 };
                    const workerMessage = {
                        type: "searchToolsByKeys",
                        payload: {
                            tools: this.toolsList,
                            keys: keys,
                            query: q,
                        },
                    };
                    this.searchWorker.postMessage(workerMessage);
                }
            } else {
                this.searchWorker.postMessage({ type: "clearFilter" });
            }
        },
        onSearch() {
            for (const [filter, value] of Object.entries(this.filterSettings)) {
                if (!value) {
                    delete this.filterSettings[filter];
                }
            }
            this.$router.push({ path: "/tools/list", query: this.filterSettings });
        },
        onToggle(toggleAdvanced) {
            this.$emit("update:show-advanced", toggleAdvanced);
        },
    },
};
</script>

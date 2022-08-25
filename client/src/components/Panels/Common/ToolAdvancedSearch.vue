<template>
    <ToolsProvider v-slot="{ loading, result: itemsLoaded }" :filter-settings="filterSettings">
        <section>
            <div class="mb-2">
                <span class="row mb-1">
                    <span class="col">
                        <h4 class="d-inline-block">Advanced Tool Search Results</h4>
                        <b-button
                            v-if="hasFilters && itemsLoaded.length !== 0"
                            class="float-right"
                            size="sm"
                            :pressed="listView"
                            :variant="listView ? 'info' : 'secondary'"
                            data-description="show list view for tools"
                            @click="listView = !listView">
                            <icon icon="list" />
                            <span>{{ "List View" | localize }}</span>
                        </b-button>
                    </span>
                </span>
                <span v-if="itemsLoaded.length !== 0 && hasFilters" class="row">
                    <span class="col d-inline-block">
                        (found {{ itemsLoaded.length }} tools for
                        <a id="popover-filters" href="javascript:void(0)">filters</a>)
                        <b-popover target="popover-filters" triggers="hover" placement="top">
                            <template v-slot:title>Filters</template>
                            <div v-for="(value, filter) in filterSettings" :key="filter">
                                <b>{{ filter }}</b
                                >: {{ value }}
                            </div>
                        </b-popover>
                    </span>
                </span>
            </div>
            <div>
                <b-alert v-if="loading" class="m-2" variant="info" show>
                    <LoadingSpan message="Loading Advanced Search Results" />
                </b-alert>
                <b-alert v-else-if="!hasFilters" class="m-2" variant="secondary" show>
                    There are no valid filters applied. Please add filters to the menu in the Tool Panel.
                </b-alert>
                <b-alert v-else-if="!itemsLoaded || itemsLoaded.length == 0" class="m-2" variant="danger" show>
                    No tools found for selected filter(s): {{ filterSettings }}
                </b-alert>
                <div v-else>
                    <ToolAdvancedSearchResults :tools="itemsLoaded" :list-view="listView" />
                </div>
                <b-button
                    v-if="hasFilters && !loading && offset > 200"
                    v-b-tooltip.hover
                    class="btn-back-to-top"
                    title="Scroll To Top"
                    variant="danger"
                    pill
                    size="lg"
                    @click="scrollToTop">
                    <icon icon="arrow-up" />
                </b-button>
            </div>
        </section>
    </ToolsProvider>
</template>

<script>
import LoadingSpan from "components/LoadingSpan";
import { ToolsProvider } from "components/providers/storeProviders";
import ToolAdvancedSearchResults from "./ToolAdvancedSearchResults";

export default {
    components: {
        LoadingSpan,
        ToolAdvancedSearchResults,
        ToolsProvider,
    },
    props: {
        name: {
            type: String,
            default: "",
        },
        panelSectionName: {
            type: String,
            default: "",
        },
        id: {
            type: String,
            default: "",
        },
        description: {
            type: String,
            default: "",
        },
    },
    data() {
        return {
            offset: 0,
            listView: false,
        };
    },
    computed: {
        filterSettings() {
            const newFilterSettings = {};
            Object.entries(this.$props).forEach(([filter, value]) => {
                if (value && value !== "") {
                    if (filter === "panelSectionName") {
                        newFilterSettings["panel_section_name"] = value;
                    } else {
                        newFilterSettings[filter] = value;
                    }
                }
            });
            return newFilterSettings;
        },
        hasFilters() {
            return Object.keys(this.filterSettings).length;
        },
    },
    beforeDestroy() {
        document.querySelector(".center-panel").removeEventListener("scroll", this.onScroll, true);
    },
    mounted() {
        document.querySelector(".center-panel").addEventListener("scroll", this.onScroll, true);
    },
    methods: {
        onScroll(e) {
            this.offset = e.target.scrollTop;
        },
        scrollToTop() {
            document.querySelector(".center-panel").scrollTop = 0;
        },
    },
};
</script>

<style>
.btn-back-to-top {
    position: fixed;
    bottom: 2em;
}
</style>

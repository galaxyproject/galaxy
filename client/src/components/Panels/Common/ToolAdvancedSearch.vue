<template>
    <ToolsProvider v-slot="{ loading, result: itemsLoaded }" :filter-settings="filterSettings">
        <section>
            <div class="mb-2">
                <span class="row mb-1">
                    <span class="col">
                        <h4 class="d-inline-block">Advanced Tool Search Results</h4>
                    </span>
                </span>
                <span v-if="itemsLoaded.length !== 0 && hasFilters" class="row">
                    <span class="col d-inline-block">
                        Found {{ itemsLoaded.length }} tools for
                        <a id="popover-filters" href="javascript:void(0)">filters</a>.
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
                    No tools found for the entered filters.
                </b-alert>
                <div v-else>
                    <ToolAdvancedSearchResults :tools="itemsLoaded" />
                </div>
                <b-button
                    v-if="hasFilters && !loading && offset > 200"
                    v-b-tooltip.noninteractive.hover
                    class="ui-btn-back-to-top btn-circle"
                    title="Scroll To Top"
                    variant="info"
                    @click="scrollToTop">
                    <i class="fa fa-arrow-up" />
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

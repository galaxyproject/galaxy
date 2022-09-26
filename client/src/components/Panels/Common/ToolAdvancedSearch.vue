<template>
    <ToolsProvider v-slot="{ loading, result: itemsLoaded }" :filter-settings="filterSettings" :toolbox="toolbox">
        <section class="overflow-auto h-100" @scroll="onScroll">
            <div class="mb-2">
                <span class="row mb-1">
                    <span class="col">
                        <h4 v-if="hasFilters" class="d-inline-block">Advanced Tool Search Results</h4>
                        <h4 v-else class="d-inline-block">Consolidated view of {{ itemsLoaded.length }} available tools.</h4>
                    </span>
                </span>
                <span v-if="itemsLoaded.length !== 0" class="row">
                    <span v-if="hasFilters" class="col d-inline-block">
                        Found {{ itemsLoaded.length }} tools for
                        <a id="popover-filters" href="javascript:void(0)">filters</a>.
                        <b-popover target="popover-filters" triggers="hover" placement="top">
                            <template v-slot:title>Filters</template>
                            <div v-for="(value, filter) in filterSettings" :key="filter">
                                <b>{{ filter }}</b
                                >: {{ value }}
                            </div>
                        </b-popover>
                        Click <a href="javascript:void(0)" @click.stop="showAllTools">here</a> for a consolidated view of all tools in this Galaxy instance. 
                    </span>
                    <span v-else class="col d-inline-block">
                        No filters applied. Please add filters to the menu in the Tool Panel.
                    </span>
                </span>
            </div>
            <div>
                <b-alert v-if="loading" class="m-2" variant="info" show>
                    <LoadingSpan message="Loading Advanced Search Results" />
                </b-alert>
                <b-alert v-else-if="!itemsLoaded || itemsLoaded.length == 0" class="m-2" variant="info" show>
                    No tools found for the entered filters.
                </b-alert>
                <div v-else>
                    <ToolAdvancedSearchResults :tools="itemsLoaded" />
                </div>
            </div>
            <ScrollToTopButton :offset="offset" @click="scrollToTop" />
        </section>
    </ToolsProvider>
</template>

<script>
import LoadingSpan from "components/LoadingSpan";
import { ToolsProvider } from "components/providers/storeProviders";
import ToolAdvancedSearchResults from "./ToolAdvancedSearchResults";
import ScrollToTopButton from "./ScrollToTopButton";

export default {
    components: {
        LoadingSpan,
        ToolAdvancedSearchResults,
        ToolsProvider,
        ScrollToTopButton,
    },
    props: {
        name: {
            type: String,
            default: "",
        },
        section: {
            type: String,
            default: "",
        },
        id: {
            type: String,
            default: "",
        },
        help: {
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
        toolbox() {
            return this.$store.getters["panels/currentPanel"];
        },
        filterSettings() {
            const newFilterSettings = {};
            Object.entries(this.$props).forEach(([filter, value]) => {
                if (value && value !== "") {
                    newFilterSettings[filter] = value;
                }
            });
            return newFilterSettings;
        },
        hasFilters() {
            return Object.keys(this.filterSettings).length;
        },
    },
    methods: {
        onScroll(e) {
            this.offset = e.target.scrollTop;
        },
        scrollToTop() {
            this.$el.scrollTop = 0;
        },
        showAllTools() {
            this.$router.push({ path: "/tools/advanced_search" });
        },
    },
};
</script>

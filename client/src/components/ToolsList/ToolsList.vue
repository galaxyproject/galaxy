<template>
    <ToolsProvider
        v-slot="{ loading, result: itemsLoaded }"
        :filter-settings="filterSettings"
        :toolbox="toolbox"
        :panel-view="panelView">
        <section class="tools-list">
            <div class="mb-2">
                <h1 class="h-lg">Search Results</h1>
                <span v-if="itemsLoaded.length !== 0" class="row">
                    <span v-if="filterCount" class="col d-inline-block d-flex align-items-baseline flex-gapx-1">
                        Found {{ itemsLoaded.length }} tools for
                        <b-button id="popover-filters" class="ui-link">
                            {{ filterCount }}
                            {{ filterCount === 1 ? "filter" : "filters" }}.
                        </b-button>
                        <b-popover target="popover-filters" triggers="hover focus" placement="bottom">
                            <template v-slot:title>Filters</template>
                            <div v-for="(value, filter) in filterSettings" :key="filter">
                                <b>{{ filter }}</b
                                >: {{ value }}
                            </div>
                        </b-popover>
                        <b-button variant="link" size="sm" @click.stop="showAllTools">
                            <FontAwesomeIcon icon="fa-times" />
                            Clear filters
                        </b-button>
                    </span>
                    <span v-else class="col d-inline-block">
                        No filters applied. Please add filters to the Advanced Tool Search in the Tool Panel.
                    </span>
                </span>
            </div>
            <div ref="scrollContainer" class="overflow-auto">
                <b-alert v-if="loading" class="m-2" variant="info" show>
                    <LoadingSpan message="Loading Advanced Search Results" />
                </b-alert>
                <b-alert v-else-if="!itemsLoaded || itemsLoaded.length == 0" class="m-2" variant="info" show>
                    No tools found for the entered filters.
                </b-alert>
                <div v-else>
                    <ToolsListTable :tools="itemsLoaded" />
                </div>
            </div>
            <ScrollToTopButton :offset="scrollTop" @click="scrollToTop" />
        </section>
    </ToolsProvider>
</template>

<script>
import LoadingSpan from "components/LoadingSpan";
import { ToolsProvider } from "components/providers/storeProviders";
import ToolsListTable from "./ToolsListTable";
import ScrollToTopButton from "./ScrollToTopButton";
import { useAnimationFrameScroll } from "composables/sensors/animationFrameScroll";
import { ref } from "vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faTimes } from "@fortawesome/free-solid-svg-icons";

library.add(faTimes);

export default {
    components: {
        LoadingSpan,
        ToolsListTable,
        ToolsProvider,
        ScrollToTopButton,
        FontAwesomeIcon,
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
    setup() {
        const scrollContainer = ref(null);
        const { scrollTop } = useAnimationFrameScroll(scrollContainer);

        return {
            scrollContainer,
            scrollTop,
        };
    },
    computed: {
        toolbox() {
            return this.$store.getters["panels/currentPanel"];
        },
        panelView() {
            return this.$store.getters["panels/currentPanelView"];
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
        filterCount() {
            return Object.keys(this.filterSettings).length;
        },
    },
    methods: {
        scrollToTop() {
            this.$refs.scrollContainer.scrollTo({ top: 0, behavior: "smooth" });
        },
        showAllTools() {
            this.$router.push({ path: "/tools/list" });
        },
    },
};
</script>

<style lang="scss" scoped>
.tools-list {
    position: relative;
    display: flex;
    flex-direction: column;
    overflow: hidden;
}
</style>

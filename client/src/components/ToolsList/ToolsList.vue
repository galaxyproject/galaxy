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
                        <GButton id="popover-filters" class="ui-link">
                            {{ filterCount }}
                            {{ filterCount === 1 ? "filter" : "filters" }}.
                        </GButton>
                        <GPopover target="popover-filters" triggers="hover focus" placement="bottom">
                            <template v-slot:title>Filters</template>
                            <div v-for="(value, filter) in filterSettings" :key="filter">
                                <b>{{ filter }}</b
                                >: {{ value }}
                            </div>
                        </GPopover>
                        <GButton variant="link" size="sm" @click.stop="showAllTools">
                            <FontAwesomeIcon icon="fa-times" />
                            Clear filters
                        </GButton>
                    </span>
                    <span v-else class="col d-inline-block">
                        No filters applied. Please add filters to the Advanced Tool Search in the Tool Panel.
                    </span>
                </span>
            </div>
            <div ref="scrollContainer" class="overflow-auto">
                <GAlert v-if="loading" class="m-2" variant="info" show>
                    <LoadingSpan message="Loading Advanced Search Results" />
                </GAlert>
                <GAlert v-else-if="!itemsLoaded || itemsLoaded.length == 0" class="m-2" variant="info" show>
                    No tools found for the entered filters.
                </GAlert>
                <div v-else>
                    <ToolsListTable :tools="itemsLoaded" />
                </div>
            </div>
            <ScrollToTopButton :offset="scrollTop" @click="scrollToTop" />
        </section>
    </ToolsProvider>
</template>

<script>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import LoadingSpan from "components/LoadingSpan";
import { ToolsProvider } from "components/providers/storeProviders";
import { useAnimationFrameScroll } from "composables/sensors/animationFrameScroll";
import { ref } from "vue";

import { GAlert, GButton, GPopover } from "@/component-library";

import ScrollToTopButton from "./ScrollToTopButton";
import ToolsListTable from "./ToolsListTable";

library.add(faTimes);

export default {
    components: {
        FontAwesomeIcon,
        GAlert,
        GButton,
        GPopover,
        LoadingSpan,
        ScrollToTopButton,
        ToolsListTable,
        ToolsProvider,
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
        owner: {
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

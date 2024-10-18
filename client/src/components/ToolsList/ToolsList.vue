<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { storeToRefs } from "pinia";
import { computed, onMounted, type Ref, ref } from "vue";
import { useRouter } from "vue-router/composables";

import { useAnimationFrameScroll } from "@/composables/sensors/animationFrameScroll";
import { useToolStore } from "@/stores/toolStore";
import { type FilterSettings, type Tool } from "@/stores/toolStoreTypes";

import ScrollToTopButton from "./ScrollToTopButton.vue";
import ToolsListTable from "./ToolsListTable.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

library.add(faTimes);

const props = defineProps({
    name: {
        type: String,
        default: "",
    },
    section: {
        type: String,
        default: "",
    },
    ontology: {
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
});

const router = useRouter();

const scrollContainer: Ref<HTMLElement | null> = ref(null);
const { scrollTop } = useAnimationFrameScroll(scrollContainer);

const toolStore = useToolStore();
const { loading } = storeToRefs(toolStore);

const filterSettings = computed(() => {
    const newFilterSettings: FilterSettings = {};
    Object.entries(props).forEach(([filter, value]) => {
        if (value && value !== "") {
            newFilterSettings[filter] = value as string;
        }
    });
    return newFilterSettings;
});

onMounted(async () => {
    await toolStore.fetchTools(filterSettings.value);
});

const filterCount = computed(() => Object.keys(filterSettings.value).length);

const itemsLoaded = computed<Tool[]>(() => Object.values(toolStore.getToolsById(filterSettings.value)));

function scrollToTop() {
    scrollContainer.value?.scrollTo({ top: 0, behavior: "smooth" });
}

function showAllTools() {
    router.push({ path: "/tools/list" });
}
</script>

<template>
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
</template>

<style lang="scss" scoped>
.tools-list {
    position: relative;
    display: flex;
    flex-direction: column;
    overflow: hidden;
}
</style>

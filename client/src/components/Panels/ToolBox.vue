<script setup lang="ts">
import { faEye, faEyeSlash } from "@fortawesome/free-regular-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BBadge } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, type ComputedRef, type Ref, ref, watch } from "vue";

import { useGlobalUploadModal } from "@/composables/globalUploadModal";
import { useToolRouting } from "@/composables/route";
import type { Tool, ToolSection as ToolSectionType } from "@/stores/toolStore";
import { useToolStore } from "@/stores/toolStore";
import localize from "@/utils/localization";

import {
    FAVORITES_KEYS,
    filterTools,
    getValidPanelItems,
    getValidToolsInCurrentView,
    getValidToolsInEachSection,
} from "./utilities";

import GButton from "../BaseComponents/GButton.vue";
import ToolSearch from "./Common/ToolSearch.vue";
import ToolSection from "./Common/ToolSection.vue";

const SECTION_IDS_TO_EXCLUDE = ["expression_tools"]; // if this isn't the Workflow Editor panel

const { openGlobalUploadModal } = useGlobalUploadModal();
const { routeToTool } = useToolRouting();

const emit = defineEmits<{
    (e: "update:show-favorites", value: boolean): void;
    (e: "onInsertTool", toolId: string, toolName: string): void;
}>();

interface Props {
    workflow?: boolean;
    useSearchWorker?: boolean;
    showFavorites?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    workflow: false,
    useSearchWorker: true,
    showFavorites: false,
});

const query = ref("");
const queryPending = ref(false);
const showSections = ref(props.workflow);
const results: Ref<string[]> = ref([]);
const resultPanel: Ref<Record<string, Tool | ToolSectionType> | null> = ref(null);
const closestTerm: Ref<string | null> = ref(null);

const toolStore = useToolStore();

const { currentPanelView, currentToolSections } = storeToRefs(toolStore);
const hasResults = computed(() => results.value.length > 0);
const queryTooShort = computed(() => query.value && query.value.length < 3);
const queryFinished = computed(() => query.value && queryPending.value != true);

// Watchers for `query` (when to apply/remove favorites, reset filter etc.)
watch(
    () => query.value,
    () => {
        queryPending.value = true;
        if (FAVORITES_KEYS.includes(query.value)) {
            emit("update:show-favorites", true);
        } else {
            emit("update:show-favorites", false);
        }
    },
);
watch(
    () => props.showFavorites,
    (newValue) => {
        if (newValue) {
            query.value = "#favorites";
        } else {
            query.value = "";
        }
    },
);
watch(
    () => currentPanelView.value,
    () => {
        query.value = "";
    },
);

/** `toolsById` from `toolStore`, except it only has valid tools for `props.workflow` value */
const localToolsById = computed(() => {
    if (toolStore.toolsById && Object.keys(toolStore.toolsById).length > 0) {
        return getValidToolsInCurrentView(
            toolStore.toolsById,
            props.workflow,
            !props.workflow ? SECTION_IDS_TO_EXCLUDE : [],
        );
    }
    return {};
});

/** `currentPanel` from `toolStore`, except it only has valid tools and sections for `props.workflow` value */
const localSectionsById = computed(() => {
    const validToolIdsInCurrentView = Object.keys(localToolsById.value);

    // Looking within each `ToolSection`, and filtering on child elements
    const sectionEntries = getValidToolsInEachSection(validToolIdsInCurrentView, currentToolSections.value);

    // Looking at each item in the panel now (not within each child)
    return getValidPanelItems(
        sectionEntries,
        validToolIdsInCurrentView,
        !props.workflow ? SECTION_IDS_TO_EXCLUDE : [],
    ) as Record<string, Tool | ToolSectionType>;
});

const toolsList = computed(() => Object.values(localToolsById.value));

/**
 * If not searching or no results, we show all tools in sections (default)
 *
 * If we have results for search, we show tools in sections or just tools,
 * based on whether `showSections` is true or false
 */
const localPanel: ComputedRef<Record<string, Tool | ToolSectionType> | null> = computed(() => {
    if (hasResults.value) {
        if (showSections.value) {
            return resultPanel.value;
        } else {
            return filterTools(localToolsById.value, results.value) as Record<string, Tool | ToolSectionType>;
        }
    } else {
        return localSectionsById.value;
    }
});

const buttonIcon = computed(() => (showSections.value ? faEyeSlash : faEye));
const buttonText = computed(() => (showSections.value ? localize("Hide Sections") : localize("Show Sections")));

function onToolClick(tool: Tool, evt: Event) {
    if (!props.workflow) {
        if (tool.id === "upload1") {
            evt.preventDefault();
            openGlobalUploadModal();
        } else if (tool.form_style === "regular") {
            evt.preventDefault();
            // encode spaces in tool.id
            routeToTool(tool.id);
        }
    } else {
        evt.preventDefault();
        emit("onInsertTool", tool.id, tool.name);
    }
}

function onResults(
    idResults: string[] | null,
    sectioned: Record<string, Tool | ToolSectionType> | null,
    closestMatch: string | null = null,
) {
    if (idResults !== null && idResults.length > 0) {
        results.value = idResults;
        resultPanel.value = sectioned;
        if (sectioned === null) {
            showSections.value = false;
        }
    } else {
        results.value = [];
        resultPanel.value = null;
    }
    closestTerm.value = closestMatch;
    queryPending.value = false;
}

function onSectionFilter(filter: string) {
    if (query.value !== filter) {
        query.value = filter;
        if (!showSections.value) {
            onToggle();
        }
    } else {
        query.value = "";
    }
}

function onSearchQuery(q: string) {
    query.value = q;
}

function onToggle() {
    showSections.value = !showSections.value;
}
</script>

<template>
    <div class="unified-panel" data-description="panel toolbox">
        <div class="unified-panel-controls">
            <ToolSearch
                :current-panel-view="currentPanelView"
                :placeholder="localize('search tools')"
                :tools-list="toolsList"
                :current-panel="localSectionsById"
                :query="query"
                :query-pending="queryPending"
                :use-worker="useSearchWorker"
                @onQuery="onSearchQuery"
                @onResults="onResults" />
            <section>
                <div v-if="hasResults && resultPanel" class="pb-2">
                    <GButton size="small" class="w-100 d-block" @click="onToggle">
                        <FontAwesomeIcon :icon="buttonIcon" />
                        <span class="mr-1">{{ buttonText }}</span>
                    </GButton>
                </div>
                <div v-else-if="queryTooShort" class="pb-2">
                    <BBadge class="alert-info w-100">Search term is too short</BBadge>
                </div>
                <div v-else-if="queryFinished && !hasResults" class="pb-2">
                    <BBadge class="alert-warning w-100">No results found</BBadge>
                </div>
                <div v-if="closestTerm" class="pb-2">
                    <BBadge class="alert-danger w-100">
                        Did you mean:
                        <i>
                            <a href="javascript:void(0)" @click="query = closestTerm">{{ closestTerm }}</a>
                        </i>
                        ?
                    </BBadge>
                </div>
            </section>
        </div>
        <div class="unified-panel-body">
            <div class="toolMenuContainer">
                <div v-if="localPanel" class="toolMenu">
                    <div v-for="(panel, key) in localPanel" :key="key">
                        <ToolSection
                            v-if="panel"
                            :category="panel || {}"
                            :query-filter="hasResults ? query : undefined"
                            :has-filter-button="hasResults && currentPanelView === 'default'"
                            @onClick="onToolClick"
                            @onFilter="onSectionFilter" />
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
.toolTitle {
    overflow-wrap: anywhere;
}
</style>

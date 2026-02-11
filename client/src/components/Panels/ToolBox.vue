<script setup lang="ts">
import { faEye, faEyeSlash } from "@fortawesome/free-regular-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BBadge } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";

import { useGlobalUploadModal } from "@/composables/globalUploadModal";
import { useToolRouting } from "@/composables/route";
import { useFavoriteSearchResults, useToolPanelFavorites } from "@/composables/toolPanelFavorites";
import type { Tool, ToolPanelItem, ToolSection as ToolSectionType, ToolSectionLabel } from "@/stores/toolStore";
import { useToolStore } from "@/stores/toolStore";
import { useUserStore } from "@/stores/userStore";
import localize from "@/utils/localization";

import { PANEL_LABEL_IDS } from "./panelViews";
import {
    buildToolEntries,
    buildToolLabel,
    buildToolSection,
    FAVORITES_KEYS,
    filterPanelByToolIds,
    filterTools,
    getValidPanelItems,
    getValidToolsInEachSection,
    getVisibleTools,
    UNSECTIONED_SECTION,
} from "./utilities";

import GButton from "../BaseComponents/GButton.vue";
import ToolSearch from "./Common/ToolSearch.vue";
import ToolSection from "./Common/ToolSection.vue";

const LOGIN_ROUTE = "/login/start";
/** Section IDs that are only valid for the workflow editor toolbox, and should be excluded from the regular toolbox. */
const WORKFLOW_ONLY_SECTION_IDS = ["expression_tools"];
const TOOLS_LIST_ROUTE = "/tools/list";

const { openGlobalUploadModal } = useGlobalUploadModal();
const { routeToTool } = useToolRouting();

const emit = defineEmits<{
    (e: "update:show-favorites", value: boolean): void;
    (e: "onInsertTool", toolId: string, toolName: string): void;
}>();

interface Props {
    /** Whether this is the toolbox in the workflow editor
     * @default false
     */
    workflow?: boolean;

    /** Whether to use a search worker for searching tools
     * @default true
     */
    useSearchWorker?: boolean;

    /** This is used to automatically apply the "#favorites"
     * filter when this prop is true.
     * @default false
     */
    showFavorites?: boolean;

    /** Whether this is the `My Tools` panel
     * @default false
     */
    favoritesDefault?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    workflow: false,
    useSearchWorker: true,
    showFavorites: false,
    favoritesDefault: false,
});

const { isAnonymous } = storeToRefs(useUserStore());

const query = ref("");
const queryPending = ref(false);
const showSections = ref(props.workflow);
const results = ref<string[]>([]);
const resultPanel = ref<Record<string, Tool | ToolSectionType> | null>(null);
const closestTerm = ref<string | null>(null);

const toolStore = useToolStore();

const { currentPanelView, currentToolSections, defaultPanelView, toolSections } = storeToRefs(toolStore);
const hasResults = computed(() => results.value.length > 0);
const queryTooShort = computed(() => query.value && query.value.length < 3);
const queryFinished = computed(() => query.value && queryPending.value != true);

// Watchers for `query` (when to apply/remove favorites, reset filter etc.)
watch(
    () => query.value,
    () => {
        queryPending.value = true;
        if (!props.favoritesDefault) {
            if (FAVORITES_KEYS.includes(query.value)) {
                emit("update:show-favorites", true);
            } else {
                emit("update:show-favorites", false);
            }
        }
    },
);
watch(
    () => props.showFavorites,
    (newValue) => {
        if (!props.favoritesDefault) {
            if (newValue) {
                query.value = "#favorites";
            } else {
                query.value = "";
            }
        }
    },
);
watch(
    () => currentPanelView.value,
    () => {
        query.value = "";
    },
);

/**
 * `toolsById` from `toolStore`
 *
 * Although, in the case of `props.workflow` (workflow editor toolbox),
 * it only has tools that are valid for the workflow editor.
 */
const localToolsById = computed(() => {
    if (toolStore.toolsById && Object.keys(toolStore.toolsById).length > 0) {
        return getVisibleTools(toolStore.toolsById, props.workflow, !props.workflow ? WORKFLOW_ONLY_SECTION_IDS : []);
    }
    return {};
});

const localToolIds = computed(() => new Set(Object.keys(localToolsById.value)));

/**
 * `currentToolSections` from `toolStore`
 *
 * Although, in the case of `props.workflow` (workflow editor toolbox),
 * it only has sections that are valid for the workflow editor.
 */
const localSectionsById = computed<Record<string, ToolPanelItem>>(() => {
    // Looking within each `ToolSection`, and filtering on child elements
    const sectionEntries = getValidToolsInEachSection(localToolIds.value, currentToolSections.value);

    // Looking at each item in the panel now (not within each child)
    return getValidPanelItems(sectionEntries, localToolIds.value, !props.workflow ? WORKFLOW_ONLY_SECTION_IDS : []);
});

/**
 * Same as `localSectionsById` except for the default panel view.
 *
 * This is used mainly to show a sectioned results view in the `My Tools` panel when there is a search query, since the
 * `My Tools` panel doesn't have sections of it's own; so we use the default view's sections as the section for each result.
 *
 * @returns
 * - `toolSections[defaultPanelView]` from `toolStore` - if the `defaultPanelView` is set
 * - `null` if the `defaultPanelView` is not set or if it doesn't have sections in `toolSections`
 */
const defaultSectionsById = computed<Record<string, ToolPanelItem> | null>(() => {
    const defaultPanelSections = defaultPanelView.value ? toolSections.value[defaultPanelView.value] : null;
    if (!defaultPanelSections) {
        return null;
    }

    // Looking within each `default` view `ToolSection`, and filtering on child elements
    const sectionEntries = getValidToolsInEachSection(localToolIds.value, defaultPanelSections);
    return getValidPanelItems(sectionEntries, localToolIds.value, !props.workflow ? WORKFLOW_ONLY_SECTION_IDS : []);
});

// Use composable for favorites and recent tools management
const {
    favoritesCollapsed,
    recentToolsCollapsed,
    favoriteToolIds,
    favoriteToolIdSet,
    favoriteToolIdsInPanel,
    recentToolIdsToShow,
    recentToolIdsToShowSet,
} = useToolPanelFavorites(localToolsById);

// Use composable for search results filtering
const { favoriteResults, nonFavoriteResults, hasMixedResults } = useFavoriteSearchResults(results, favoriteToolIdSet);

const toolsCount = computed(() => toolsList.value.length);

/** Whether to show the "empty favorites" alert:
 *  - If the current panel is the `My Tools` panel
 *  - There is no search query
 *  - The user has no favorite tools
 */
const showEmptyFavorites = computed(() => props.favoritesDefault && !query.value && favoriteToolIds.value.length === 0);

const resultsSet = computed(() => new Set(results.value));
const nonFavoriteResultsSet = computed(() => new Set(nonFavoriteResults.value));

/**
 * A panel with just one section that has all tools in it. Only used in the case that
 * `defaultSectionsById` is `null` (`default` panel view doesn't exist or doesn't have sections yet)
 */
const allToolsPanel = computed(() => {
    return {
        [PANEL_LABEL_IDS.ALL_TOOLS_SECTION]: {
            model_class: "ToolSection",
            id: PANEL_LABEL_IDS.ALL_TOOLS_SECTION,
            name: localize("All tools"),
            tools: Object.keys(localToolsById.value),
        },
    } as Record<string, Tool | ToolSectionType>;
});

/** The `currentPanel` which will be used by the tool search to search tools */
const searchPanelSections = computed(() => {
    if (props.favoritesDefault) {
        return defaultSectionsById.value || allToolsPanel.value;
    }
    return localSectionsById.value;
});

const toolsList = computed(() => Object.values(localToolsById.value));

/**
 * For search results, this creates a panel which - if results are not mixed between favorite
 * and non-favorite tools - contains just the tools that are in the search results; if
 * results are mixed, it creates two sections: one for favorite results and one for non-favorite results.
 */
const flatResultsPanel = computed<Record<string, Tool | ToolSectionLabel> | null>(() => {
    if (!hasResults.value) {
        return null;
    }

    if (!hasMixedResults.value) {
        return filterTools(localToolsById.value, results.value);
    }

    const entries: Array<[string, Tool | ToolSectionLabel]> = [];
    entries.push([
        PANEL_LABEL_IDS.FAVORITES_RESULTS_LABEL,
        buildToolLabel(PANEL_LABEL_IDS.FAVORITES_RESULTS_LABEL, localize("Favorites")),
    ]);
    if (!favoritesCollapsed.value) {
        entries.push(...buildToolEntries(favoriteResults.value, localToolsById.value));
    }
    entries.push([
        PANEL_LABEL_IDS.SEARCH_RESULTS_LABEL,
        buildToolLabel(PANEL_LABEL_IDS.SEARCH_RESULTS_LABEL, localize("Search results")),
    ]);
    entries.push(...buildToolEntries(nonFavoriteResults.value, localToolsById.value));
    return Object.fromEntries(entries);
});

/**
 * The custom/client built `My Tools` panel when `props.favoritesDefault` is true.
 * This panel shows favorite and recent tools when there is no search query.
 *
 * Unlike panel views returned by the `toolStore`, this panel is built here on the client side.
 */
const favoritesDefaultPanel = computed<Record<string, ToolPanelItem> | null>(() => {
    if (!props.favoritesDefault || query.value) {
        return null;
    }
    const entries: Array<[string, ToolPanelItem]> = [];
    const favorites = favoriteToolIdsInPanel.value;
    const recents = recentToolIdsToShow.value;

    entries.push([
        PANEL_LABEL_IDS.FAVORITES_LABEL,
        buildToolLabel(PANEL_LABEL_IDS.FAVORITES_LABEL, localize("Favorites")),
    ]);
    if (!favoritesCollapsed.value) {
        if (showEmptyFavorites.value) {
            entries.push([
                PANEL_LABEL_IDS.FAVORITES_EMPTY_ALERT,
                buildToolLabel(PANEL_LABEL_IDS.FAVORITES_EMPTY_ALERT, ""),
            ]);
        } else {
            entries.push(...buildToolEntries(favorites, localToolsById.value));
        }
    }
    if (recents.length > 0) {
        entries.push([
            PANEL_LABEL_IDS.RECENT_TOOLS_LABEL,
            buildToolLabel(PANEL_LABEL_IDS.RECENT_TOOLS_LABEL, localize("Recent tools")),
        ]);
        if (!recentToolsCollapsed.value) {
            entries.push(...buildToolEntries(recents, localToolsById.value));
        }
    }
    return Object.fromEntries(entries);
});

/**
 * For tool search results, this returns a results panel.
 */
const sectionedResultsPanel = computed<Record<string, ToolPanelItem> | null>(() => {
    if (!hasResults.value) {
        return null;
    }

    /** The base panel to filter results from.
     *
     * If `props.favoritesDefault` is true, we use the `default` panel view's sections
     * from `toolStore` as the base panel to filter results from.
     * Otherwise, we use the `resultPanel` returned from the search.
     */
    const basePanel =
        props.favoritesDefault && defaultSectionsById.value ? defaultSectionsById.value : resultPanel.value;
    if (!basePanel) {
        return null;
    }

    if (!hasMixedResults.value) {
        return props.favoritesDefault && defaultSectionsById.value
            ? filterPanelByToolIds(basePanel, resultsSet.value)
            : basePanel;
    }

    const otherResultsPanel = filterPanelByToolIds(basePanel, nonFavoriteResultsSet.value);
    const favoritesSection = buildToolSection(
        PANEL_LABEL_IDS.FAVORITES_RESULTS_SECTION,
        localize("Favorites"),
        favoriteResults.value,
    );
    return {
        [PANEL_LABEL_IDS.FAVORITES_RESULTS_SECTION]: favoritesSection,
        ...otherResultsPanel,
    };
});

/**
 * If not searching or no results, we show all tools in sections (default)
 *
 * If we have results for search, we show tools in sections or just tools,
 * based on whether `showSections` is true or false
 */
const localPanel = computed<Record<string, ToolPanelItem> | null>(() => {
    // We are in the `My Tools` panel and there is no search query, show the custom `My Tools` panel with favorites and recents sections
    if (props.favoritesDefault && !query.value) {
        return favoritesDefaultPanel.value || {};
    }

    // There is a search query and results, show the search results panel (sectioned or flat based on `showSections`)
    if (hasResults.value) {
        if (showSections.value) {
            return sectionedResultsPanel.value || flatResultsPanel.value;
        } else {
            return flatResultsPanel.value;
        }
    }
    if (props.favoritesDefault) {
        return {};
    }
    return localSectionsById.value;
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

/** Stores the localStorage state of collapsed labels for the favorites and recents sections in the `My Tools` panel. */
const collapsedLabels = computed(() => {
    if (props.favoritesDefault) {
        return {
            [PANEL_LABEL_IDS.FAVORITES_LABEL]: favoritesCollapsed.value,
            [PANEL_LABEL_IDS.FAVORITES_RESULTS_LABEL]: favoritesCollapsed.value,
            [PANEL_LABEL_IDS.RECENT_TOOLS_LABEL]: recentToolsCollapsed.value,
        };
    }
    return null;
});

function onLabelToggle(labelId: string) {
    if (!props.favoritesDefault) {
        return;
    }
    if (labelId === PANEL_LABEL_IDS.FAVORITES_LABEL || labelId === PANEL_LABEL_IDS.FAVORITES_RESULTS_LABEL) {
        favoritesCollapsed.value = !favoritesCollapsed.value;
    } else if (labelId === PANEL_LABEL_IDS.RECENT_TOOLS_LABEL) {
        recentToolsCollapsed.value = !recentToolsCollapsed.value;
    }
}
</script>

<template>
    <div class="unified-panel" data-description="panel toolbox">
        <div class="unified-panel-controls">
            <ToolSearch
                :current-panel-view="currentPanelView"
                :placeholder="localize('search tools')"
                :tools-list="toolsList"
                :current-panel="searchPanelSections"
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
                    <div v-for="(panelItem, key) in localPanel" :key="key">
                        <div v-if="panelItem?.id === PANEL_LABEL_IDS.FAVORITES_EMPTY_ALERT" class="tool-panel-empty">
                            <BAlert variant="info" show>
                                <template v-if="!isAnonymous">
                                    You haven't favorited any tools yet. Search the toolbox or use
                                    <GButton
                                        class="ml-1"
                                        size="small"
                                        color="blue"
                                        :to="TOOLS_LIST_ROUTE"
                                        data-description="discover-tools">
                                        Discover Tools
                                    </GButton>
                                    to explore {{ toolsCount }} community curated tools.
                                </template>
                                <template v-else>
                                    You need to
                                    <GButton
                                        class="ml-1"
                                        size="small"
                                        color="blue"
                                        :to="LOGIN_ROUTE"
                                        data-description="login button">
                                        Login
                                    </GButton>
                                    to favorite tools and have them appear in this section.
                                </template>
                            </BAlert>
                        </div>
                        <ToolSection
                            v-else-if="panelItem"
                            :category="panelItem"
                            :query-filter="hasResults ? query : undefined"
                            :has-filter-button="
                                hasResults &&
                                currentPanelView === 'default' &&
                                panelItem.id !== PANEL_LABEL_IDS.FAVORITES_RESULTS_SECTION &&
                                panelItem.id !== UNSECTIONED_SECTION.id
                            "
                            :search-active="hasResults"
                            :show-favorite-button="recentToolIdsToShowSet.has(panelItem.id)"
                            :collapsed-labels="collapsedLabels"
                            @onClick="onToolClick"
                            @onFilter="onSectionFilter"
                            @onLabelToggle="onLabelToggle" />
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
.tool-panel-empty {
    padding: 0.5rem;
}
</style>

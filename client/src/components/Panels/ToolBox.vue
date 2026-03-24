<script setup lang="ts">
import { faEye, faEyeSlash } from "@fortawesome/free-regular-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BBadge } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";
import draggable from "vuedraggable";

import { isTool, isToolSection } from "@/api/tools";
import { useGlobalUploadModal } from "@/composables/globalUploadModal";
import { useToolRouting } from "@/composables/route";
import { useFavoriteSearchResults, useToolPanelFavorites } from "@/composables/toolPanelFavorites";
import { useToast } from "@/composables/toast";
import type { Tool, ToolPanelItem, ToolSection as ToolSectionType, ToolSectionLabel } from "@/stores/toolStore";
import { useToolStore } from "@/stores/toolStore";
import { useUserStore } from "@/stores/userStore";
import type { FavoriteOrderEntry } from "@/stores/users/queries";
import ariaAlert from "@/utils/ariaAlert";
import localize from "@/utils/localization";

import {
    FAVORITE_EDAM_OPERATION_SECTION_PREFIX,
    FAVORITE_EDAM_TOPIC_SECTION_PREFIX,
    FAVORITE_TAG_SECTION_PREFIX,
    MY_PANEL_VIEW_ID,
    PANEL_LABEL_IDS,
} from "./panelViews";
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
import ToolItem from "./Common/Tool.vue";
import ToolPanelLabel from "./Common/ToolPanelLabel.vue";
import ToolSection from "./Common/ToolSection.vue";

const LOGIN_ROUTE = "/login/start";
/** Section IDs that are only valid for the workflow editor toolbox, and should be excluded from the regular toolbox. */
const WORKFLOW_ONLY_SECTION_IDS = ["expression_tools"];
const TOOLS_LIST_ROUTE = "/tools/list";

const { openGlobalUploadModal } = useGlobalUploadModal();
const { routeToTool } = useToolRouting();
const Toast = useToast();

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

const userStore = useUserStore();
const { isAnonymous } = storeToRefs(userStore);

const query = ref("");
const queryPending = ref(false);
const showSections = ref(props.workflow);
const results = ref<string[]>([]);
const resultPanel = ref<Record<string, Tool | ToolSectionType> | null>(null);
const closestTerm = ref<string | null>(null);

const toolStore = useToolStore();

const { currentPanelView, currentToolSections, defaultPanelView, toolSections, toolTagsLoaded } = storeToRefs(toolStore);
const hasResults = computed(() => results.value.length > 0);
const queryTooShort = computed(() => query.value && query.value.length < 3);
const queryFinished = computed(() => query.value && queryPending.value != true);
const showMyToolsLanding = computed(() => props.favoritesDefault && !query.value);

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
    const defaultPanelSections =
        toolSections.value["default"] ||
        (defaultPanelView.value && defaultPanelView.value !== MY_PANEL_VIEW_ID
            ? toolSections.value[defaultPanelView.value]
            : null);
    if (!defaultPanelSections) {
        return null;
    }

    // Looking within each `default` view `ToolSection`, and filtering on child elements
    const sectionEntries = getValidToolsInEachSection(localToolIds.value, defaultPanelSections);
    const validSections = getValidPanelItems(
        sectionEntries,
        localToolIds.value,
        !props.workflow ? WORKFLOW_ONLY_SECTION_IDS : [],
    );
    return Object.keys(validSections).length > 0 ? validSections : null;
});

// Use composable for favorites and recent tools management
const {
    favoritesCollapsed,
    recentToolsCollapsed,
    favoriteToolIds,
    favoriteTags,
    favoriteEdamOperations,
    favoriteEdamTopics,
    favoriteOrder,
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
const showEmptyFavorites = computed(
    () =>
        props.favoritesDefault &&
        !query.value &&
        favoriteToolIdsInPanel.value.length === 0 &&
        favoriteTagSections.value.length === 0 &&
        favoriteEdamOperationSections.value.length === 0 &&
        favoriteEdamTopicSections.value.length === 0,
);

const recentToolsLabel = computed(() =>
    buildToolLabel(PANEL_LABEL_IDS.RECENT_TOOLS_LABEL, localize("Recent tools")),
);
const favoritesLabel = computed(() =>
    buildToolLabel(PANEL_LABEL_IDS.FAVORITES_LABEL, localize("Favorites")),
);

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
const recentToolsInPanel = computed(() =>
    recentToolIdsToShow.value
        .map((toolId) => localToolsById.value[toolId])
        .filter((tool): tool is Tool => Boolean(tool)),
);

const orderedToolIds = computed(() => {
    const ordered: string[] = [];
    const seen = new Set<string>();
    const panelsToFlatten = [defaultSectionsById.value, localSectionsById.value];

    const appendToolId = (toolId: string) => {
        if (localToolsById.value[toolId] && !seen.has(toolId)) {
            seen.add(toolId);
            ordered.push(toolId);
        }
    };

    for (const panel of panelsToFlatten) {
        if (!panel) {
            continue;
        }
        for (const item of Object.values(panel)) {
            if ("tools" in item && item.tools) {
                item.tools.forEach((toolOrLabel) => {
                    if (typeof toolOrLabel === "string") {
                        appendToolId(toolOrLabel);
                    }
                });
            } else if ("id" in item && "name" in item && !("text" in item)) {
                appendToolId(item.id);
            }
        }
    }

    Object.keys(localToolsById.value).forEach(appendToolId);
    return ordered;
});

const favoriteTagSections = computed(() =>
    favoriteTags.value
        .map((tag) => {
            const matchingToolIds = orderedToolIds.value.filter((toolId) =>
                localToolsById.value[toolId]?.tool_tags?.includes(tag),
            );
            return matchingToolIds.length > 0
                ? buildToolSection(`${FAVORITE_TAG_SECTION_PREFIX}${encodeURIComponent(tag)}`, tag, matchingToolIds)
                : null;
        })
        .filter((section): section is ToolSectionType => section !== null),
);

const edamOperationDefinitions = computed(() => {
    const operations = toolStore.panelSections("ontology:edam_operations");
    return operations.reduce(
        (acc, operation) => {
            acc[operation.id] = operation;
            return acc;
        },
        {} as Record<string, ToolSectionType>,
    );
});

const edamTopicDefinitions = computed(() => {
    const topics = toolStore.panelSections("ontology:edam_topics");
    return topics.reduce(
        (acc, topic) => {
            acc[topic.id] = topic;
            return acc;
        },
        {} as Record<string, ToolSectionType>,
    );
});

const favoriteEdamOperationSections = computed<ToolSectionType[]>(() =>
    favoriteEdamOperations.value.flatMap((operationId) => {
        const matchingToolIds = orderedToolIds.value.filter((toolId) =>
            localToolsById.value[toolId]?.edam_operations?.includes(operationId),
        );
        if (matchingToolIds.length === 0) {
            return [];
        }
        const operation = edamOperationDefinitions.value[operationId];
        const section = buildToolSection(
            `${FAVORITE_EDAM_OPERATION_SECTION_PREFIX}${encodeURIComponent(operationId)}`,
            operation?.name || operationId,
            matchingToolIds,
        );
        if (operation?.description) {
            section.description = operation.description;
        }
        return [section];
    }),
);

const favoriteEdamTopicSections = computed<ToolSectionType[]>(() =>
    favoriteEdamTopics.value.flatMap((topicId) => {
        const matchingToolIds = orderedToolIds.value.filter((toolId) =>
            localToolsById.value[toolId]?.edam_topics?.includes(topicId),
        );
        if (matchingToolIds.length === 0) {
            return [];
        }
        const topic = edamTopicDefinitions.value[topicId];
        const section = buildToolSection(
            `${FAVORITE_EDAM_TOPIC_SECTION_PREFIX}${encodeURIComponent(topicId)}`,
            topic?.name || topicId,
            matchingToolIds,
        );
        if (topic?.description) {
            section.description = topic.description;
        }
        return [section];
    }),
);

type FavoriteTopLevelItem = {
    favoriteKey: string;
    orderEntry: FavoriteOrderEntry;
    panelItem: Tool | ToolSectionType;
};

function favoriteEntryKey(orderEntry: FavoriteOrderEntry) {
    return `${orderEntry.object_type}:${encodeURIComponent(orderEntry.object_id)}`;
}

const visibleFavoriteTopLevelItems = computed<FavoriteTopLevelItem[]>(() => {
    const favoriteItemsByKey = new Map<string, FavoriteTopLevelItem>();

    for (const toolId of favoriteToolIdsInPanel.value) {
        const tool = localToolsById.value[toolId];
        if (tool) {
            const orderEntry: FavoriteOrderEntry = { object_type: "tools", object_id: toolId };
            favoriteItemsByKey.set(favoriteEntryKey(orderEntry), {
                favoriteKey: favoriteEntryKey(orderEntry),
                orderEntry,
                panelItem: tool,
            });
        }
    }

    for (const section of favoriteTagSections.value) {
        const tagName = decodeURIComponent(section.id.slice(FAVORITE_TAG_SECTION_PREFIX.length));
        const orderEntry: FavoriteOrderEntry = { object_type: "tags", object_id: tagName };
        favoriteItemsByKey.set(favoriteEntryKey(orderEntry), {
            favoriteKey: favoriteEntryKey(orderEntry),
            orderEntry,
            panelItem: section,
        });
    }

    for (const section of favoriteEdamOperationSections.value) {
        const operationId = decodeURIComponent(section.id.slice(FAVORITE_EDAM_OPERATION_SECTION_PREFIX.length));
        const orderEntry: FavoriteOrderEntry = { object_type: "edam_operations", object_id: operationId };
        favoriteItemsByKey.set(favoriteEntryKey(orderEntry), {
            favoriteKey: favoriteEntryKey(orderEntry),
            orderEntry,
            panelItem: section,
        });
    }

    for (const section of favoriteEdamTopicSections.value) {
        const topicId = decodeURIComponent(section.id.slice(FAVORITE_EDAM_TOPIC_SECTION_PREFIX.length));
        const orderEntry: FavoriteOrderEntry = { object_type: "edam_topics", object_id: topicId };
        favoriteItemsByKey.set(favoriteEntryKey(orderEntry), {
            favoriteKey: favoriteEntryKey(orderEntry),
            orderEntry,
            panelItem: section,
        });
    }

    const ordered: FavoriteTopLevelItem[] = [];
    const seenKeys = new Set<string>();
    for (const orderEntry of favoriteOrder.value) {
        const key = favoriteEntryKey(orderEntry);
        const panelItem = favoriteItemsByKey.get(key);
        if (panelItem && !seenKeys.has(key)) {
            seenKeys.add(key);
            ordered.push(panelItem);
        }
    }

    for (const [key, panelItem] of favoriteItemsByKey.entries()) {
        if (!seenKeys.has(key)) {
            seenKeys.add(key);
            ordered.push(panelItem);
        }
    }

    return ordered;
});

const draggableFavoriteItems = ref<FavoriteTopLevelItem[]>([]);
const syncingFavoriteOrder = ref(false);

watch(
    () => visibleFavoriteTopLevelItems.value,
    (newItems) => {
        if (!syncingFavoriteOrder.value) {
            draggableFavoriteItems.value = [...newItems];
        }
    },
    { immediate: true },
);

function mergeFavoriteOrder(updatedVisibleOrder: FavoriteOrderEntry[]) {
    const visibleKeys = new Set(visibleFavoriteTopLevelItems.value.map((item) => favoriteEntryKey(item.orderEntry)));
    const reorderedQueue = [...updatedVisibleOrder];
    const mergedOrder: FavoriteOrderEntry[] = [];

    for (const entry of favoriteOrder.value) {
        if (visibleKeys.has(favoriteEntryKey(entry))) {
            const reorderedEntry = reorderedQueue.shift();
            if (reorderedEntry) {
                mergedOrder.push(reorderedEntry);
            }
        } else {
            mergedOrder.push(entry);
        }
    }

    for (const remainingEntry of reorderedQueue) {
        mergedOrder.push(remainingEntry);
    }

    return mergedOrder;
}

async function onFavoriteDragStart() {
    syncingFavoriteOrder.value = true;
}

async function onFavoriteDragEnd() {
    const reorderedVisibleOrder = draggableFavoriteItems.value.map((item) => item.orderEntry);
    const mergedOrder = mergeFavoriteOrder(reorderedVisibleOrder);
    const sameOrder =
        mergedOrder.length === favoriteOrder.value.length &&
        mergedOrder.every(
            (entry, index) =>
                entry.object_type === favoriteOrder.value[index]?.object_type &&
                entry.object_id === favoriteOrder.value[index]?.object_id,
        );

    syncingFavoriteOrder.value = false;

    if (sameOrder) {
        return;
    }

    try {
        await userStore.reorderFavorites(mergedOrder);
        ariaAlert("favorites reordered");
    } catch {
        draggableFavoriteItems.value = [...visibleFavoriteTopLevelItems.value];
        Toast.error("Failed to reorder favorites.");
        ariaAlert("failed to reorder favorites");
    }
}

watch(
    () => [props.favoritesDefault, favoriteTags.value.join("\0"), toolTagsLoaded.value] as const,
    async ([favoritesDefault, serializedFavoriteTags, tagsLoaded]) => {
        const catalogAlreadyHasToolTags =
            Object.keys(toolStore.toolsById).length > 0 &&
            Object.values(toolStore.toolsById).every((tool) => tool.tool_tags !== undefined);
        if (!favoritesDefault || !serializedFavoriteTags || tagsLoaded || catalogAlreadyHasToolTags) {
            return;
        }
        await toolStore.fetchTools(undefined, { includeToolTags: true });
    },
    { immediate: true },
);

watch(
    () => [props.favoritesDefault, favoriteEdamOperations.value.join("\0"), Boolean(toolSections.value["ontology:edam_operations"])] as const,
    async ([favoritesDefault, serializedFavoriteEdamOperations, hasOntologySections]) => {
        if (!favoritesDefault || !serializedFavoriteEdamOperations || hasOntologySections) {
            return;
        }
        await toolStore.fetchToolSections("ontology:edam_operations");
    },
    { immediate: true },
);

watch(
    () => [props.favoritesDefault, favoriteEdamTopics.value.join("\0"), Boolean(toolSections.value["ontology:edam_topics"])] as const,
    async ([favoritesDefault, serializedFavoriteEdamTopics, hasOntologySections]) => {
        if (!favoritesDefault || !serializedFavoriteEdamTopics || hasOntologySections) {
            return;
        }
        await toolStore.fetchToolSections("ontology:edam_topics");
    },
    { immediate: true },
);

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
    const recents = recentToolIdsToShow.value;
    const favorites = favoriteToolIdsInPanel.value;

    if (recents.length > 0) {
        entries.push([
            PANEL_LABEL_IDS.RECENT_TOOLS_LABEL,
            buildToolLabel(PANEL_LABEL_IDS.RECENT_TOOLS_LABEL, localize("Recent tools")),
        ]);
        if (!recentToolsCollapsed.value) {
            entries.push(...buildToolEntries(recents, localToolsById.value));
        }
    }
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
            entries.push(...favoriteTagSections.value.map((section) => [section.id, section] as [string, ToolPanelItem]));
            entries.push(
                ...favoriteEdamOperationSections.value.map((section) => [section.id, section] as [string, ToolPanelItem]),
            );
            entries.push(...favoriteEdamTopicSections.value.map((section) => [section.id, section] as [string, ToolPanelItem]));
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
                <div v-if="showMyToolsLanding" class="toolMenu">
                    <ToolPanelLabel
                        v-if="recentToolIdsToShow.length > 0"
                        :definition="recentToolsLabel"
                        :collapsed="collapsedLabels?.[PANEL_LABEL_IDS.RECENT_TOOLS_LABEL]"
                        @toggle="onLabelToggle" />
                    <template v-if="recentToolIdsToShow.length > 0 && !recentToolsCollapsed">
                        <ToolItem
                            v-for="tool in recentToolsInPanel"
                            :key="`recent-tool-${tool.id}`"
                            :tool="tool"
                            show-favorite-button
                            @onClick="onToolClick" />
                    </template>

                    <ToolPanelLabel
                        :definition="favoritesLabel"
                        :collapsed="collapsedLabels?.[PANEL_LABEL_IDS.FAVORITES_LABEL]"
                        @toggle="onLabelToggle" />
                    <div v-if="!favoritesCollapsed">
                        <div v-if="showEmptyFavorites" class="tool-panel-empty">
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
                        <draggable
                            v-else
                            v-model="draggableFavoriteItems"
                            data-description="favorites-top-level-list"
                            :disabled="isAnonymous"
                            :force-fallback="true"
                            handle=".favorite-top-level-drag-target"
                            ghost-class="favorite-top-level-ghost"
                            drag-class="favorite-top-level-drag"
                            chosen-class="favorite-top-level-chosen"
                            @start="onFavoriteDragStart"
                            @end="onFavoriteDragEnd">
                            <div
                                v-for="favoriteItem in draggableFavoriteItems"
                                :key="favoriteItem.favoriteKey"
                                class="favorite-top-level-item"
                                :data-description="`favorite-top-level-item-${favoriteItem.orderEntry.object_type}`"
                                :data-favorite-type="favoriteItem.orderEntry.object_type"
                                :data-favorite-id="favoriteItem.orderEntry.object_id">
                                <ToolSection
                                    v-if="isToolSection(favoriteItem.panelItem)"
                                    :category="favoriteItem.panelItem"
                                    :collapsed-labels="collapsedLabels"
                                    show-drag-handle
                                    @onClick="onToolClick"
                                    @onFilter="onSectionFilter"
                                    @onLabelToggle="onLabelToggle" />
                                <ToolItem
                                    v-else-if="isTool(favoriteItem.panelItem)"
                                    :tool="favoriteItem.panelItem"
                                    show-drag-handle
                                    @onClick="onToolClick" />
                            </div>
                        </draggable>
                    </div>
                </div>
                <div v-else-if="localPanel" class="toolMenu">
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

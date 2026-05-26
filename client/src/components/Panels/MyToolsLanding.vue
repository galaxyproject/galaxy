<script setup lang="ts">
/**
 * The "My Tools" panel landing — recent tools at the top, favorited tools and
 * favorited tag/EDAM sections below, drag-and-drop to reorder. Mounted by the
 * parent `ToolBox` only when `props.favoritesDefault === true` and there is
 * no active search query, keeping all the My Tools-specific reactivity off
 * the default tool panel hot path.
 */
import { BAlert } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";
import draggable from "vuedraggable";

import { isTool, isToolSection } from "@/api/tools";
import { useToast } from "@/composables/toast";
import { useToolPanelFavorites } from "@/composables/toolPanelFavorites";
import type { Tool, ToolPanelItem, ToolSection as ToolSectionType } from "@/stores/toolStore";
import { useToolStore } from "@/stores/toolStore";
import type { FavoriteOrderEntry } from "@/stores/users/queries";
import { useUserStore } from "@/stores/userStore";
import ariaAlert from "@/utils/ariaAlert";
import localize from "@/utils/localization";

import {
    FAVORITE_EDAM_OPERATION_SECTION_PREFIX,
    FAVORITE_EDAM_TOPIC_SECTION_PREFIX,
    FAVORITE_TAG_SECTION_PREFIX,
    PANEL_LABEL_IDS,
} from "./panelViews";
import { buildToolLabel, buildToolSection } from "./utilities";

import GButton from "../BaseComponents/GButton.vue";
import ToolItem from "./Common/Tool.vue";
import ToolPanelLabel from "./Common/ToolPanelLabel.vue";
import ToolSection from "./Common/ToolSection.vue";

const LOGIN_ROUTE = "/login/start";
const TOOLS_LIST_ROUTE = "/tools/list";

interface Props {
    /** Live `toolsById` slice already filtered by parent for visibility (workflow vs. analysis). */
    localToolsById: Record<string, Tool>;
    /** Default panel sections from the toolStore — used to flatten tool order for tag/EDAM grouping. */
    defaultSectionsById: Record<string, ToolPanelItem> | null;
    /** Current panel sections from the toolStore. */
    localSectionsById: Record<string, ToolPanelItem>;
    /** Tool count to surface in the empty-state CTA. */
    toolsCount: number;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "onClick", tool: Tool, evt: Event): void;
    (e: "onFilter", filter: string): void;
    (e: "onLabelToggle", labelId: string): void;
}>();

const Toast = useToast();
const userStore = useUserStore();
const { isAnonymous } = storeToRefs(userStore);

const toolStore = useToolStore();
const { toolSections, toolTagsLoaded } = storeToRefs(toolStore);

const {
    favoritesCollapsed,
    recentToolsCollapsed,
    favoriteTags,
    favoriteEdamOperations,
    favoriteEdamTopics,
    favoriteOrder,
    favoriteToolIdsInPanel,
    recentToolIdsToShow,
} = useToolPanelFavorites(computed(() => props.localToolsById));

const recentToolsLabel = computed(() => buildToolLabel(PANEL_LABEL_IDS.RECENT_TOOLS_LABEL, localize("Recent tools")));
const favoritesLabel = computed(() => buildToolLabel(PANEL_LABEL_IDS.FAVORITES_LABEL, localize("Favorites")));

const collapsedLabels = computed(() => ({
    [PANEL_LABEL_IDS.FAVORITES_LABEL]: favoritesCollapsed.value,
    [PANEL_LABEL_IDS.FAVORITES_RESULTS_LABEL]: favoritesCollapsed.value,
    [PANEL_LABEL_IDS.RECENT_TOOLS_LABEL]: recentToolsCollapsed.value,
}));

const recentToolsInPanel = computed(() =>
    recentToolIdsToShow.value
        .map((toolId) => props.localToolsById[toolId])
        .filter((tool): tool is Tool => Boolean(tool)),
);

/**
 * Flatten the parent's panel sections into a single ordered list of tool ids.
 * Used to keep tools inside favorite-tag / favorite-EDAM sections in the same
 * order they appear in the default panel view.
 */
const orderedToolIds = computed(() => {
    const ordered: string[] = [];
    const seen = new Set<string>();
    const panelsToFlatten = [props.defaultSectionsById, props.localSectionsById];

    const appendToolId = (toolId: string) => {
        if (props.localToolsById[toolId] && !seen.has(toolId)) {
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

    Object.keys(props.localToolsById).forEach(appendToolId);
    return ordered;
});

const favoriteTagSections = computed(() =>
    favoriteTags.value
        .map((tag) => {
            const matchingToolIds = orderedToolIds.value.filter((toolId) =>
                props.localToolsById[toolId]?.tool_tags?.includes(tag),
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
            props.localToolsById[toolId]?.edam_operations?.includes(operationId),
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
            props.localToolsById[toolId]?.edam_topics?.includes(topicId),
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

const favoriteMetadataPending = computed(
    () =>
        (favoriteTags.value.length > 0 && !toolTagsLoaded.value) ||
        (favoriteEdamOperations.value.length > 0 && !toolSections.value["ontology:edam_operations"]) ||
        (favoriteEdamTopics.value.length > 0 && !toolSections.value["ontology:edam_topics"]),
);

const showEmptyFavorites = computed(
    () =>
        !favoriteMetadataPending.value &&
        favoriteToolIdsInPanel.value.length === 0 &&
        favoriteTagSections.value.length === 0 &&
        favoriteEdamOperationSections.value.length === 0 &&
        favoriteEdamTopicSections.value.length === 0,
);

type FavoriteTopLevelItem = {
    favoriteKey: string;
    orderEntry: FavoriteOrderEntry;
    panelItem: Tool | ToolSectionType;
};

// Convention: favorite ids are stored on the server in raw form (e.g. "Get Data"
// or an EDAM URI containing a colon). For client-side identity — Vue `:key`
// values, section ids built with FAVORITE_*_SECTION_PREFIX, and Map lookups
// — we URI-encode the id so the type:id separator and any ":" inside the id
// don't collide. DOM `data-favorite-id` attributes use the raw id; only
// internal lookup keys are encoded.
function favoriteEntryKey(orderEntry: FavoriteOrderEntry) {
    return `${orderEntry.object_type}:${encodeURIComponent(orderEntry.object_id)}`;
}

const visibleFavoriteTopLevelItems = computed<FavoriteTopLevelItem[]>(() => {
    const favoriteItemsByKey = new Map<string, FavoriteTopLevelItem>();

    for (const toolId of favoriteToolIdsInPanel.value) {
        const tool = props.localToolsById[toolId];
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
        ariaAlert(localize("favorites reordered"));
    } catch {
        draggableFavoriteItems.value = [...visibleFavoriteTopLevelItems.value];
        Toast.error(localize("Failed to reorder favorites."));
        ariaAlert(localize("failed to reorder favorites"));
    }
}

// Lazy-load the curated tag mapping the first time the user has any favorited
// tags — kept here (not in the parent) so the default tool panel never pays
// the network cost.
watch(
    () => [favoriteTags.value.join("\0"), toolTagsLoaded.value] as const,
    async ([serializedFavoriteTags, tagsLoaded]) => {
        if (!serializedFavoriteTags || tagsLoaded) {
            return;
        }
        await toolStore.fetchToolTagsMapping();
    },
    { immediate: true },
);

// Same lazy-load idiom for EDAM operation/topic panel sections — only fetched
// once the user has any favorited operations/topics.
watch(
    () => [favoriteEdamOperations.value.join("\0"), Boolean(toolSections.value["ontology:edam_operations"])] as const,
    async ([serializedFavoriteEdamOperations, hasOntologySections]) => {
        if (!serializedFavoriteEdamOperations || hasOntologySections) {
            return;
        }
        await toolStore.fetchToolSections("ontology:edam_operations");
    },
    { immediate: true },
);

watch(
    () => [favoriteEdamTopics.value.join("\0"), Boolean(toolSections.value["ontology:edam_topics"])] as const,
    async ([serializedFavoriteEdamTopics, hasOntologySections]) => {
        if (!serializedFavoriteEdamTopics || hasOntologySections) {
            return;
        }
        await toolStore.fetchToolSections("ontology:edam_topics");
    },
    { immediate: true },
);

function onToolClick(tool: Tool, evt: Event) {
    emit("onClick", tool, evt);
}

function onSectionFilter(filter: string) {
    emit("onFilter", filter);
}

function onLabelToggle(labelId: string) {
    // Persist the collapsed state ourselves — the parent passes it up purely
    // for any shell-level reactions (e.g. analytics). The composable refs are
    // backed by localStorage and shared with the favorites-results split in
    // search mode, so the parent doesn't need to mirror the toggle.
    if (labelId === PANEL_LABEL_IDS.FAVORITES_LABEL || labelId === PANEL_LABEL_IDS.FAVORITES_RESULTS_LABEL) {
        favoritesCollapsed.value = !favoritesCollapsed.value;
    } else if (labelId === PANEL_LABEL_IDS.RECENT_TOOLS_LABEL) {
        recentToolsCollapsed.value = !recentToolsCollapsed.value;
    }
    emit("onLabelToggle", labelId);
}
</script>

<template>
    <div class="toolMenu" data-description="my-tools-landing">
        <ToolPanelLabel
            v-if="recentToolIdsToShow.length > 0"
            :definition="recentToolsLabel"
            :collapsed="collapsedLabels[PANEL_LABEL_IDS.RECENT_TOOLS_LABEL]"
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
            :collapsed="collapsedLabels[PANEL_LABEL_IDS.FAVORITES_LABEL]"
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
</template>

<style scoped>
.tool-panel-empty {
    padding: 0.5rem;
}
</style>

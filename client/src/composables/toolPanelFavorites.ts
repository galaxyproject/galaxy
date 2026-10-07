import { storeToRefs } from "pinia";
import { computed, type ComputedRef, type Ref } from "vue";

import type { Tool } from "@/stores/toolStore";
import { useUserStore } from "@/stores/userStore";

import { usePersistentToggle } from "./persistentToggle";

function extractBaseToolId(toolId: string, tool: Tool | undefined) {
    if (tool?.version && toolId.endsWith(`/${tool.version}`)) {
        return toolId.slice(0, -tool.version.length - 1);
    }
    return undefined;
}

/**
 * Composable for managing favorites and recent tools in the tool panel.
 * Provides computed properties for favorites/recent tool filtering and persistent collapse state.
 */
export function useToolPanelFavorites(
    localToolsById: Ref<Record<string, Tool>>,
    panelToolIds?: ComputedRef<Set<string>>,
) {
    const { currentFavorites, recentTools } = storeToRefs(useUserStore());

    // Collapse state with localStorage persistence (user-specific)
    const { toggled: favoritesCollapsed, toggle: toggleFavorites } = usePersistentToggle(
        "tool-panel-favorites-collapsed",
    );
    const { toggled: recentToolsCollapsed, toggle: toggleRecent } = usePersistentToggle("tool-panel-recent-collapsed");

    // Derived favorites data
    const favoriteToolIds = computed(() => currentFavorites.value.tools || []);
    const favoriteTags = computed(() => currentFavorites.value.tags || []);
    const favoriteEdamOperations = computed(() => currentFavorites.value.edam_operations || []);
    const favoriteEdamTopics = computed(() => currentFavorites.value.edam_topics || []);
    const favoriteOrder = computed(() => currentFavorites.value.order || []);
    const favoriteToolIdSet = computed(() => new Set(favoriteToolIds.value));
    const favoriteToolIdsInPanel = computed(() =>
        favoriteToolIds.value.filter((toolId) => !!localToolsById.value[toolId]),
    );

    // Derived recent tools data
    const recentToolIds = computed(() => [...new Set(recentTools.value || [])]);
    const panelUniqueToolIds = computed(() => {
        const baseToolIdMap = new Map<string, string>();
        for (const toolId of panelToolIds?.value || []) {
            const baseToolId = extractBaseToolId(toolId, localToolsById.value[toolId]);
            if (baseToolId) {
                baseToolIdMap.set(baseToolId, toolId);
            }
        }
        return baseToolIdMap;
    });
    const recentToolIdsInPanel = computed(() => {
        const seenToolIds = new Set<string>();
        return recentToolIds.value
            .map((toolId) => {
                if (!panelToolIds || panelToolIds.value.has(toolId)) {
                    return toolId;
                }

                const baseToolId = extractBaseToolId(toolId, localToolsById.value[toolId]);
                return baseToolId ? panelUniqueToolIds.value.get(baseToolId) : undefined;
            })
            .filter((toolId): toolId is string => !!toolId && !!localToolsById.value[toolId])
            .filter((toolId) => {
                if (seenToolIds.has(toolId)) {
                    return false;
                }
                seenToolIds.add(toolId);
                return true;
            });
    });
    const recentToolIdsToShow = computed(() =>
        recentToolIdsInPanel.value.filter((toolId) => !favoriteToolIdSet.value.has(toolId)),
    );
    const recentToolIdsToShowSet = computed(() => new Set(recentToolIdsToShow.value));

    return {
        // Collapse state
        favoritesCollapsed,
        recentToolsCollapsed,
        toggleFavorites,
        toggleRecent,
        // Favorites
        favoriteToolIds,
        favoriteTags,
        favoriteEdamOperations,
        favoriteEdamTopics,
        favoriteOrder,
        favoriteToolIdSet,
        favoriteToolIdsInPanel,
        // Recent tools
        recentToolIds,
        recentToolIdsInPanel,
        recentToolIdsToShow,
        recentToolIdsToShowSet,
    };
}

/**
 * Composable for computing search results split by favorites vs non-favorites.
 * Used when displaying search results with favorites prominently.
 */
export function useFavoriteSearchResults(
    results: Ref<string[]>,
    favoriteToolIdSet: ComputedRef<Set<string>>,
): {
    favoriteResults: ComputedRef<string[]>;
    nonFavoriteResults: ComputedRef<string[]>;
    /** `true` if there are both favorite and non-favorite results */
    hasMixedResults: ComputedRef<boolean>;
} {
    const favoriteResults = computed(() => results.value.filter((id) => favoriteToolIdSet.value.has(id)));
    const nonFavoriteResults = computed(() => results.value.filter((id) => !favoriteToolIdSet.value.has(id)));
    const hasMixedResults = computed(() => favoriteResults.value.length > 0 && nonFavoriteResults.value.length > 0);

    return {
        favoriteResults,
        nonFavoriteResults,
        hasMixedResults,
    };
}

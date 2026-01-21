import { storeToRefs } from "pinia";
import { computed, type ComputedRef, type Ref } from "vue";

import type { Tool } from "@/stores/toolStore";
import { useUserStore } from "@/stores/userStore";

import { usePersistentToggle } from "./persistentToggle";

/**
 * Composable for managing favorites and recent tools in the tool panel.
 * Provides computed properties for favorites/recent tool filtering and persistent collapse state.
 */
export function useToolPanelFavorites(localToolsById: Ref<Record<string, Tool>>) {
    const { currentFavorites, recentTools } = storeToRefs(useUserStore());

    // Collapse state with localStorage persistence (user-specific)
    const { toggled: favoritesCollapsed, toggle: toggleFavorites } = usePersistentToggle(
        "tool-panel-favorites-collapsed",
    );
    const { toggled: recentToolsCollapsed, toggle: toggleRecent } = usePersistentToggle("tool-panel-recent-collapsed");

    // Derived favorites data
    const favoriteToolIds = computed(() => currentFavorites.value.tools || []);
    const favoriteToolIdSet = computed(() => new Set(favoriteToolIds.value));
    const favoriteToolIdsInPanel = computed(() =>
        favoriteToolIds.value.filter((toolId) => !!localToolsById.value[toolId]),
    );

    // Derived recent tools data
    const recentToolIds = computed(() => recentTools.value || []);
    const recentToolIdsInPanel = computed(() => recentToolIds.value.filter((toolId) => !!localToolsById.value[toolId]));
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

import type { Decorator } from "@storybook/vue3-vite";
import { getFakeRegisteredUser } from "@tests/test-data";
import { getFakeTool } from "@tests/test-data/tools";
import { HttpResponse } from "msw";
import { getActivePinia, type Pinia, type StoreGeneric } from "pinia";
import { h, nextTick, onBeforeUnmount, onUnmounted, ref, watch } from "vue";
import type { AnyUser } from "@/api";
import { http } from "@/api/client/__mocks__/http";
import toolsListUntyped from "@/components/ToolsView/testData/toolsList.json";
import toolsListInPanelUntyped from "@/components/ToolsView/testData/toolsListInPanel.json";
import { useHashedUserId } from "@/composables/hashedUserId";
import { type Tool, type ToolSection, useToolStore } from "@/stores/toolStore";
import type { FavoriteSummary } from "@/stores/users/queries";
import { useUserStore } from "@/stores/userStore";

export const TOOLBOX_TOOLS = toolsListUntyped as unknown as Tool[];

export const TOOLBOX_PANEL = toolsListInPanelUntyped as unknown as Record<string, Tool | ToolSection>;

export const TOOLBOX_USER = getFakeRegisteredUser({ username: "toolbox-user" });

// Installed FastQC versions already used by the tool-card stories.
export const FASTQC_VERSIONS = ["0.73+galaxy0", "0.74+galaxy1"].map((version) =>
    getFakeTool({
        id: `toolshed.g2.bx.psu.edu/repos/devteam/fastqc/fastqc/${version}`,
        name: "FastQC",
        description: "Read Quality reports",
        version,
    }),
);

// test/functional/tools/for_workflows/mapper.xml supplies this annotation.
export const EDAM_MAPPER = getFakeTool({
    id: "mapper",
    name: "Mapper",
    version: "0.1.0",
    edam_operations: ["operation_3198"],
    edam_topics: ["topic_0102"],
});

export interface ToolBoxState {
    tools?: Tool[];
    toolSections?: Record<string, Record<string, Tool | ToolSection>>;
    favorites?: Partial<FavoriteSummary>;
    recentTools?: string[];
    currentPanelView?: string;
    user?: AnyUser;
}

/** Non-prop page state belongs in typed parameters, rather than component args. */
export function toolBoxState(state: ToolBoxState) {
    return { toolBoxState: state };
}

const SEEDED_STORAGE_PREFIXES = [
    "user-store-recent-tools",
    "tool-store-view",
    "toggle-state-tool-panel-favorites-collapsed",
    "toggle-state-tool-panel-recent-collapsed",
];

const USER_STORAGE_PREFIXES = [
    "history-store-pinned-histories",
    "user-flags-store-show-break-warning",
    "user-flags-store-preferred-form-select",
    "user-flags-store-show-storage-operations-helper-popover",
    "user-store-list-view-preferences",
    "user-store-seen-upload-help",
    "user-store-history-panel-width",
    "user-store-chat-panel-width",
];

function favoriteSummary(favorites: Partial<FavoriteSummary> = {}): FavoriteSummary {
    return {
        tools: [...(favorites.tools ?? [])],
        tags: [...(favorites.tags ?? [])],
        edam_operations: [...(favorites.edam_operations ?? [])],
        edam_topics: [...(favorites.edam_topics ?? [])],
        order: (favorites.order ?? []).map((entry) => ({ ...entry })),
    };
}

// Sequential mounts for the same viewer must finish reused-store watcher writes before
// the next fixture snapshots storage. Concurrent fixtures sharing these stores are unsupported.
let pendingCleanup: Promise<void> | undefined;

function captureStore(pinia: Pinia | undefined, id: string, fields?: string[]) {
    const previousStore = pinia?._s.get(id);
    const previousState = pinia?.state.value[id];
    const previousValues = { ...previousState };
    return {
        reused: !!previousStore,
        restore(store: StoreGeneric | undefined) {
            if (!store || !pinia) {
                return;
            }
            if (previousStore) {
                for (const field of fields ?? Object.keys(previousValues)) {
                    store.$state[field] = previousValues[field];
                }
            } else {
                store.$dispose();
                if (previousState === undefined) {
                    delete pinia.state.value[id];
                } else {
                    Object.assign(previousState, previousValues);
                    pinia.state.value[id] = previousState;
                }
            }
        },
    };
}

/**
 * The enclosing tool panel has loaded its catalog, viewer and preferences.
 * Supports fresh Pinia or sequential reuse with the same viewer; reused stores retain
 * their identities and unseeded state. Settle child requests before unmounting.
 */
export const withToolBoxState: Decorator = (story, { parameters }) => ({
    setup() {
        const state: ToolBoxState = parameters.toolBoxState ?? {};
        const viewer = state.user === undefined ? TOOLBOX_USER : state.user;
        const pinia = getActivePinia();
        const previousUser = captureStore(pinia, "userStore", ["currentUser", "currentPreferences", "recentTools"]);
        const previousTools = captureStore(pinia, "toolStore", [
            "toolsById",
            "toolSections",
            "defaultPanelView",
            "currentPanelView",
        ]);
        const previousFlags = captureStore(pinia, "userFlagsStore");
        const ready = ref(false);
        const savedStorage = new Map<string, string | null>();
        let alive = true;
        let starting = false;
        let userStore: ReturnType<typeof useUserStore> | undefined;
        let toolStore: ReturnType<typeof useToolStore> | undefined;
        // Resolve the viewer first: the app's hash is shared across mounts. Constructing
        // stores afterward prevents them binding to the preceding viewer's storage key.
        const { hashedUserId } = useHashedUserId(ref(viewer));
        watch(
            hashedUserId,
            async (hash) => {
                if (starting || ready.value || (!viewer?.isAnonymous && viewer && !hash)) {
                    return;
                }
                starting = true;
                if (pendingCleanup) {
                    await pendingCleanup;
                }
                if (!alive) {
                    return;
                }
                if (hash) {
                    for (const prefix of [...SEEDED_STORAGE_PREFIXES, ...USER_STORAGE_PREFIXES]) {
                        const key = `${prefix}-${hash}`;
                        savedStorage.set(key, localStorage.getItem(key));
                        if (SEEDED_STORAGE_PREFIXES.includes(prefix)) {
                            localStorage.removeItem(key);
                        }
                    }
                }
                userStore = useUserStore(pinia);
                userStore.currentUser = viewer;
                userStore.currentPreferences = { favorites: favoriteSummary(state.favorites) };
                userStore.recentTools = [...(state.recentTools ?? [])];
                toolStore = useToolStore(pinia);
                toolStore.toolsById = Object.fromEntries((state.tools ?? TOOLBOX_TOOLS).map((tool) => [tool.id, tool]));
                toolStore.toolSections = state.toolSections ?? { default: TOOLBOX_PANEL };
                toolStore.defaultPanelView = "default";
                toolStore.currentPanelView = state.currentPanelView ?? "my_panel";
                ready.value = true;
            },
            { immediate: true },
        );
        let restoreAfterUnmount: (() => void) | undefined;
        onUnmounted(() => restoreAfterUnmount?.());
        onBeforeUnmount(() => {
            alive = false;
            if (!ready.value) {
                return;
            }
            previousFlags.restore(pinia?._s.get("userFlagsStore"));
            previousTools.restore(toolStore);
            previousUser.restore(userStore);
            const restoreStorage = () => {
                for (const [key, value] of savedStorage) {
                    if (value === null) {
                        localStorage.removeItem(key);
                    } else {
                        localStorage.setItem(key, value);
                    }
                }
            };
            if (previousUser.reused || previousTools.reused || previousFlags.reused) {
                // Reused refs keep watchers; flush restored values before restoring keys.
                const cleanup = nextTick().then(restoreStorage);
                pendingCleanup = cleanup;
                void cleanup.then(() => {
                    if (pendingCleanup === cleanup) {
                        pendingCleanup = undefined;
                    }
                });
            } else {
                restoreAfterUnmount = restoreStorage;
            }
        });
        return () => (ready.value ? h(story()) : null);
    },
});

function currentFavorites(): FavoriteSummary {
    return favoriteSummary(useUserStore().currentFavorites);
}

/** Real favorites mutations return the complete updated FavoriteObjectsSummary. */
export const toolboxHandlers = {
    toolTags: http.get("/api/tags/tool_tags", ({ response }) =>
        response(200).json(Object.fromEntries(TOOLBOX_TOOLS.map((tool) => [tool.id, tool.tool_tags ?? []]))),
    ),
    removeFavorite: http.delete("/api/users/{user_id}/favorites/{object_type}/{object_id}", ({ params, response }) => {
        const favorites = currentFavorites();
        const type = params.object_type as "tools" | "tags" | "edam_operations" | "edam_topics";
        favorites[type] = favorites[type].filter((id) => id !== params.object_id);
        favorites.order = favorites.order.filter(
            (entry) => entry.object_type !== type || entry.object_id !== params.object_id,
        );
        return response(200).json(favorites);
    }),
    addFavorite: http.put("/api/users/{user_id}/favorites/{object_type}", async ({ params, request, response }) => {
        const { object_id } = await request.json();
        const favorites = currentFavorites();
        const type = params.object_type as "tools" | "tags" | "edam_operations" | "edam_topics";
        if (!favorites[type].includes(object_id)) {
            favorites[type].push(object_id);
            favorites.order.push({ object_type: type, object_id });
        }
        return response(200).json(favorites);
    }),
    favoriteOrder: http.put("/api/users/{user_id}/favorites/order", async ({ request, response }) => {
        const { order } = await request.json();
        return response(200).json({ ...currentFavorites(), order });
    }),
    panel: http.untyped.get("/api/tool_panels/:panelView", ({ params }) =>
        HttpResponse.json(useToolStore().toolSections[String(params.panelView)] ?? TOOLBOX_PANEL),
    ),
};

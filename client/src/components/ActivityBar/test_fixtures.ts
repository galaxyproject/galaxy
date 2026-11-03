import type { Decorator } from "@storybook/vue3-vite";
import { getFakeDatasetSummary } from "@tests/test-data/datasets";
import { getActivePinia, setActivePinia } from "pinia";
import { h, nextTick, onBeforeUnmount, ref } from "vue";

import { http } from "@/api/client/__mocks__/http";
import { useHashedUserId } from "@/composables/hashedUserIdFromUserStore";
import { convertDropData, defaultActivities } from "@/stores/activitySetup";
import { useActivityStore } from "@/stores/activityStore";
import type { Activity } from "@/stores/activityStoreTypes";
import { useUnprivilegedToolStore } from "@/stores/unprivilegedToolStore";
import { ensureDefined } from "@/utils/assertions";

export const ACTIVITY_SETTINGS_SCOPE = "story-activity-settings";
export const DATASET_BOOKMARK = ensureDefined(
    convertDropData(
        getFakeDatasetSummary({
            id: "a21d6f8c7e4b9031",
            history_id: "f2db41e1fa331b3e",
            name: "RNA-seq counts",
        }),
    ),
);

export interface ActivitySettingsState {
    /** Saved visibility and custom bookmarks in this activity bar. */
    activities?: Activity[];
}

export function activitySettingsState(state: ActivitySettingsState) {
    return { activitySettingsState: state };
}

// Only pending cleanup remains registered; completed scopes are removed.
const pendingScopeCleanup = new Map<string, Promise<void>>();

/** Runs inside the signed-viewer decorator, after its user hash has resolved. */
export const withActivitySettingsState: Decorator = (story, { args, parameters }) => ({
    setup() {
        const state: ActivitySettingsState = parameters.activitySettingsState ?? {};
        const scope = String(args.activityBarId);
        const pinia = ensureDefined(getActivePinia());
        const { hashedUserId } = useHashedUserId();
        const owner = `${scope}-${hashedUserId.value}`;
        const ready = ref(false);
        let mounted = true;
        let release: (() => void) | undefined;
        async function initialize() {
            // Vue does not await teardown hooks. A same-scope remount must wait for
            // any earlier debounce and restoration before reading these exact keys.
            await pendingScopeCleanup.get(owner);
            if (!mounted) {
                return;
            }
            const savedStorage = new Map<string, string | null>();
            for (const field of ["activities", "current-side-bar", "side-panel-width"]) {
                const key = `activity-store-${field}-${owner}`;
                savedStorage.set(key, localStorage.getItem(key));
                localStorage.removeItem(key);
            }
            setActivePinia(pinia);
            const existed = pinia._s.has(`activityStore-${scope}`);
            const store = useActivityStore(scope);
            const permissionsExisted = pinia._s.has("unprivilegedToolStore");
            const permissions = useUnprivilegedToolStore(pinia);
            const previous = store.getAll();
            const previousSideBar = store.toggledSideBar;
            const previousWidth = store.sidePanelWidth;
            // Drain the private 10ms debounce before the settings can render.
            const initialSync = store.sync();
            release = () => {
                if (!permissionsExisted) {
                    permissions.$dispose();
                    delete pinia.state.value[permissions.$id];
                }
                if (!existed) {
                    store.$dispose();
                    delete pinia.state.value[store.$id];
                }
                const cleanup = (async () => {
                    await initialSync;
                    if (existed) {
                        store.setAll(previous);
                        store.toggledSideBar = previousSideBar;
                        store.sidePanelWidth = previousWidth;
                    }
                    await nextTick();
                    for (const [key, value] of savedStorage) {
                        if (value === null) {
                            localStorage.removeItem(key);
                        } else {
                            localStorage.setItem(key, value);
                        }
                    }
                })();
                pendingScopeCleanup.set(owner, cleanup);
                cleanup.finally(() => {
                    if (pendingScopeCleanup.get(owner) === cleanup) {
                        pendingScopeCleanup.delete(owner);
                    }
                });
            };
            await initialSync;
            if (mounted) {
                store.setAll((state.activities ?? defaultActivities).map((activity) => ({ ...activity })));
                ready.value = true;
            }
        }
        initialize();
        onBeforeUnmount(() => {
            mounted = false;
            release?.();
        });
        return () => (ready.value ? h(story()) : null);
    },
});

export const activitySettingsHandlers = {
    permittedTools: http.get("/api/unprivileged_tools", ({ response }) => response(200).json([])),
    deniedTools: http.get("/api/unprivileged_tools", ({ response }) =>
        response("4XX").json(
            { err_code: 403005, err_msg: "User is not allowed to run unprivileged tools" },
            { status: 403 },
        ),
    ),
};

import type { Decorator } from "@storybook/vue3-vite";
import { getFakeRegisteredUser } from "@tests/test-data";
import { getActivePinia } from "pinia";
import { h, nextTick, onBeforeUnmount, onUnmounted, ref, watch } from "vue";

import { type components, isRegisteredUser } from "@/api";
import { http } from "@/api/client/__mocks__/http";
import { useHashedUserId } from "@/composables/hashedUserId";
import { type BroadcastNotification, useBroadcastsStore } from "@/stores/broadcastsStore";
import { useUserStore } from "@/stores/userStore";

export const HOUR = 60 * 60 * 1000;
export const DAY = 24 * HOUR;

export interface BroadcastScenario extends Pick<BroadcastNotification, "id" | "variant"> {
    subject: string;
    message: string;
    /** Offsets from now, in ms. */
    publishedIn: number;
    expiresIn: number;
}

/** A broadcast timed from `now`, created a day before it's published, or a day before now if that's earlier. */
export function broadcast(
    now: number,
    { subject, message, publishedIn, expiresIn, ...rest }: BroadcastScenario,
    naiveUtc = false,
) {
    const format = (time: number) => {
        const iso = new Date(time).toISOString();
        return naiveUtc ? iso.replace("Z", "") : iso;
    };
    const created = format(now + Math.min(publishedIn, 0) - DAY);
    return {
        ...rest,
        source: "admin",
        category: "broadcast",
        create_time: created,
        update_time: created,
        publication_time: format(now + publishedIn),
        expiration_time: format(now + expiresIn),
        content: { category: "broadcast", subject, message },
    } satisfies BroadcastNotification;
}

const USER_STORAGE_PREFIXES = [
    "user-store-list-view-preferences",
    "user-store-seen-upload-help",
    "user-store-history-panel-width",
    "user-store-chat-panel-width",
    "user-store-recent-tools",
];

export const BROADCAST_VIEWER = getFakeRegisteredUser({
    id: "9a834bf7c1e652d0",
    username: "broadcast-preview",
    is_admin: true,
});

interface BroadcastsState {
    notifications: () => BroadcastNotification[];
}

/** Generate time-relative data when the story mounts, rather than at module load. */
export function broadcastsState(notifications: () => BroadcastNotification[]) {
    return { broadcastsState: { notifications } satisfies BroadcastsState };
}

let pendingCleanup: Promise<void> | undefined;

/** Seeds notices and preserves this viewer's dismissal and store-initialization keys. */
export const withBroadcastsState: Decorator = (story, { parameters }) => ({
    setup() {
        const pinia = getActivePinia();
        if (!pinia) {
            throw new Error("Broadcast stories need Pinia.");
        }
        const oldUser = pinia._s.get("userStore") as ReturnType<typeof useUserStore> | undefined;
        const oldBroadcasts = pinia._s.get("broadcastsStore") as ReturnType<typeof useBroadcastsStore> | undefined;
        const previousUser = oldUser?.currentUser ?? null;
        if (oldBroadcasts && (!isRegisteredUser(previousUser) || previousUser.id !== BROADCAST_VIEWER.id)) {
            throw new Error("Reused broadcast stores must already belong to the preview viewer.");
        }
        const previousUserState = pinia.state.value.userStore;
        const previousUserValues = previousUserState && { ...previousUserState };
        const previousBroadcastState = pinia.state.value.broadcastsStore;
        const previousBroadcastValues = previousBroadcastState && {
            ...previousBroadcastState,
            broadcasts: [...(previousBroadcastState.broadcasts ?? [])],
            dismissedBroadcasts: { ...(previousBroadcastState.dismissedBroadcasts ?? {}) },
        };
        const previousBroadcasts = oldBroadcasts?.broadcasts;
        const previousDismissed = oldBroadcasts?.dismissedBroadcasts;
        const ready = ref(false);
        let alive = true;
        let starting = false;
        const savedStorage = new Map<string, string | null>();
        const expectedHash = ref<string | null>(null);
        let userStore: ReturnType<typeof useUserStore> | undefined;
        let store: ReturnType<typeof useBroadcastsStore> | undefined;
        // Resolve the dedicated viewer before creating any store with persistent refs.
        const { hashedUserId } = useHashedUserId(ref(BROADCAST_VIEWER));
        const salt = localStorage.getItem("local-storage-salt");
        if (salt === null) {
            throw new Error("The viewer hash must initialize its storage salt.");
        }
        void crypto.subtle.digest("SHA-256", new TextEncoder().encode(BROADCAST_VIEWER.id + salt)).then((buffer) => {
            if (alive) {
                expectedHash.value = window.btoa(String.fromCharCode(...new Uint8Array(buffer)));
            }
        });
        watch(
            [hashedUserId, expectedHash],
            async ([hash, expected]) => {
                if (!hash || hash !== expected || starting || ready.value) {
                    return;
                }
                starting = true;
                if (pendingCleanup) {
                    await pendingCleanup;
                }
                if (!alive || hashedUserId.value !== hash) {
                    starting = false;
                    return;
                }
                // Store initialization can write these five preference keys too. Capture
                // their raw values first, but clear only the scenario's dismissal key.
                for (const prefix of ["dismissed-broadcasts", ...USER_STORAGE_PREFIXES]) {
                    const key = `${prefix}-${hash}`;
                    savedStorage.set(key, localStorage.getItem(key));
                }
                localStorage.removeItem(`dismissed-broadcasts-${hash}`);
                userStore = useUserStore(pinia);
                userStore.currentUser = BROADCAST_VIEWER;
                store = useBroadcastsStore(pinia);
                store.dismissedBroadcasts = {};
                const state: BroadcastsState | undefined = parameters.broadcastsState;
                store.broadcasts = state?.notifications() ?? [];
                ready.value = true;
            },
            { immediate: true },
        );
        let restoreAfterUnmount: (() => void) | undefined;
        onUnmounted(() => restoreAfterUnmount?.());
        onBeforeUnmount(() => {
            alive = false;
            if (!ready.value || !store || !userStore) {
                return;
            }
            if (oldBroadcasts) {
                store.broadcasts = previousBroadcasts ?? [];
                store.dismissedBroadcasts = previousDismissed ?? {};
            } else {
                store.$dispose();
                if (previousBroadcastState === undefined) {
                    delete pinia.state.value.broadcastsStore;
                } else {
                    Object.assign(previousBroadcastState, previousBroadcastValues);
                    pinia.state.value.broadcastsStore = previousBroadcastState;
                }
            }
            if (oldUser) {
                userStore.currentUser = previousUser ?? null;
            } else {
                userStore.$dispose();
                if (previousUserState === undefined) {
                    delete pinia.state.value.userStore;
                } else {
                    Object.assign(previousUserState, previousUserValues);
                    pinia.state.value.userStore = previousUserState;
                }
            }
            const restoreStorage = () => {
                for (const [key, value] of savedStorage) {
                    if (value === null) {
                        localStorage.removeItem(key);
                    } else {
                        localStorage.setItem(key, value);
                    }
                }
            };
            if (oldBroadcasts) {
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

export const SCHEDULED_BROADCAST_ID = "97ac384eddac6e10";
export const PUBLISHED_BROADCAST_ID = "a08cab2912ce4311";

/** Real admin form responses; relative timestamps are generated when requested. */
export function broadcastFormHandlers() {
    return {
        broadcast: http.get("/api/notifications/broadcast/{notification_id}", ({ params, response }) => {
            const scheduled = params.notification_id === SCHEDULED_BROADCAST_ID;
            if (!scheduled && params.notification_id !== PUBLISHED_BROADCAST_ID) {
                return response("4XX").json({ err_code: 404001, err_msg: "Broadcast not found" }, { status: 404 });
            }
            const notification: BroadcastNotification = broadcast(
                Date.now(),
                {
                    id: params.notification_id,
                    variant: scheduled ? "info" : "warning",
                    subject: scheduled ? "Scheduled maintenance" : "Service capacity notice",
                    message: scheduled
                        ? "Galaxy will undergo maintenance this weekend."
                        : "Storage capacity is limited while maintenance is in progress.",
                    publishedIn: scheduled ? DAY : -DAY,
                    expiresIn: 7 * DAY,
                },
                true,
            );
            notification.content.action_links = [
                { action_name: "Galaxy documentation", link: "https://docs.galaxyproject.org/" },
            ];
            return response(200).json(notification);
        }),
        createBroadcast: http.post("/api/notifications/broadcast", async ({ request, response }) => {
            const payload = await request.json();
            const now = new Date().toISOString().replace("Z", "");
            const notification: components["schemas"]["NotificationResponse"] = {
                ...payload,
                id: "6a83cc4912b5e707",
                create_time: now,
                update_time: now,
                publication_time: payload.publication_time ?? now,
                expiration_time:
                    payload.expiration_time ?? new Date(Date.now() + 180 * DAY).toISOString().replace("Z", ""),
            };
            return response(200).json({ notification, total_notifications_sent: 1 });
        }),
        updateBroadcast: http.put("/api/notifications/broadcast/{notification_id}", ({ params, response }) => {
            if (
                params.notification_id !== SCHEDULED_BROADCAST_ID &&
                params.notification_id !== PUBLISHED_BROADCAST_ID
            ) {
                return response("4XX").json({ err_code: 404001, err_msg: "Broadcast not found" }, { status: 404 });
            }
            return response(204).empty();
        }),
    };
}

import { defineStore } from "pinia";
import { computed, ref, watch } from "vue";

import { GalaxyApi } from "@/api";
import type { NotificationChanges, UserNotification, UserNotificationsBatchUpdateRequest } from "@/api/notifications";
import { useResourceWatcher } from "@/composables/resourceWatcher";
import { useSSE } from "@/composables/useNotificationSSE";
import { rethrowSimple } from "@/utils/simple-error";
import { mergeObjectListsById } from "@/utils/utils";

import { useBroadcastsStore } from "./broadcastsStore";

const ACTIVE_POLLING_INTERVAL = 30000; // 30 seconds
const INACTIVE_POLLING_INTERVAL = ACTIVE_POLLING_INTERVAL * 20; // 10 minutes

export const useNotificationsStore = defineStore("notificationsStore", () => {
    const broadcastsStore = useBroadcastsStore();

    const totalUnreadCount = ref<number>(0);
    const notifications = ref<UserNotification[]>([]);

    const loadingNotifications = ref<boolean>(false);
    const lastNotificationUpdate = ref<Date | null>(null);
    const wantSSE = ref(true);

    const unreadNotifications = computed(() => notifications.value.filter((n) => !n.seen_time));

    // --- SSE setup (listen only for notification event types) ---
    const NOTIFICATION_EVENT_TYPES = ["notification_update", "broadcast_update", "notification_status"] as const;
    const {
        connect: sseConnect,
        disconnect: sseDisconnect,
        connected: sseConnected,
    } = useSSE(handleSSEEvent, NOTIFICATION_EVENT_TYPES);

    // --- Polling fallback ---
    const { startWatchingResource: startPolling, stopWatchingResource: stopPolling } = useResourceWatcher(
        getNotificationStatus,
        {
            shortPollingInterval: ACTIVE_POLLING_INTERVAL,
            longPollingInterval: INACTIVE_POLLING_INTERVAL,
        },
    );

    function stopWatchingNotifications() {
        sseDisconnect();
        stopPolling();
    }

    // When SSE connection drops and doesn't recover, fall back to polling
    watch(sseConnected, (isConnected) => {
        if (!isConnected && wantSSE.value) {
            // SSE disconnected but we still want updates — don't start polling
            // immediately, EventSource will auto-reconnect. Only if useSSE is
            // set to false (after too many errors) do we fall back.
        }
    });

    watch(wantSSE, (wantSSE) => {
        if (!wantSSE) {
            sseDisconnect();
            startPolling();
        }
    });

    function handleSSEEvent(event: MessageEvent) {
        try {
            const data = JSON.parse(event.data);
            switch (event.type) {
                case "notification_update":
                    notifications.value = mergeObjectListsById(
                        notifications.value,
                        [data as UserNotification],
                        "create_time",
                        "desc",
                    );
                    updateUnreadCount();
                    break;
                case "broadcast_update":
                    broadcastsStore.updateBroadcasts([data]);
                    break;
                case "notification_status":
                    // Full catch-up on reconnect (same shape as GET /api/notifications/status)
                    totalUnreadCount.value = data.total_unread_count;
                    notifications.value = mergeObjectListsById(
                        notifications.value,
                        data.notifications as UserNotification[],
                        "create_time",
                        "desc",
                    );
                    broadcastsStore.updateBroadcasts(data.broadcasts);
                    break;
            }
            lastNotificationUpdate.value = new Date();
        } catch (e) {
            console.error("Error handling SSE event:", e);
        }
    }

    async function loadNotifications() {
        const { data, error } = await GalaxyApi().GET("/api/notifications");

        if (error) {
            rethrowSimple(error);
        }

        const useNotifications = data as UserNotification[]; // We are sure this cannot be a broadcast
        notifications.value = mergeObjectListsById(useNotifications, [], "create_time", "desc");
    }

    async function getNotificationStatus() {
        try {
            if (!lastNotificationUpdate.value) {
                loadingNotifications.value = true;
                await broadcastsStore.loadBroadcasts();
                await loadNotifications();
                updateUnreadCount();
            } else {
                const { data, error } = await GalaxyApi().GET("/api/notifications/status", {
                    params: {
                        query: {
                            since: lastNotificationUpdate.value.toISOString().replace("Z", ""),
                        },
                    },
                });

                if (error) {
                    rethrowSimple(error);
                }

                totalUnreadCount.value = data.total_unread_count;
                notifications.value = mergeObjectListsById(
                    notifications.value,
                    data.notifications as UserNotification[],
                    "create_time",
                    "desc",
                );
                broadcastsStore.updateBroadcasts(data.broadcasts);
            }
            lastNotificationUpdate.value = new Date();
        } catch (e) {
            console.error(e);
        } finally {
            loadingNotifications.value = false;
        }
    }

    async function startWatchingNotifications() {
        // Always do an initial load first
        if (!lastNotificationUpdate.value) {
            try {
                loadingNotifications.value = true;
                await broadcastsStore.loadBroadcasts();
                await loadNotifications();
                updateUnreadCount();
                lastNotificationUpdate.value = new Date();
            } catch (e) {
                console.error(e);
            } finally {
                loadingNotifications.value = false;
            }
        }

        if (wantSSE.value) {
            sseConnect();
        } else {
            startPolling();
        }
    }

    async function updateBatchNotification(request: UserNotificationsBatchUpdateRequest) {
        const { error } = await GalaxyApi().PUT("/api/notifications", {
            body: request,
        });

        if (error) {
            rethrowSimple(error);
        }

        if (request.changes.deleted) {
            notifications.value = notifications.value.filter((n) => !request.notification_ids.includes(n.id));
        }
        // If not using SSE, trigger a poll to refresh state
        if (!sseConnected.value) {
            startWatchingNotifications();
        }
    }

    async function updateNotification(notification: UserNotification, changes: NotificationChanges) {
        return updateBatchNotification({ notification_ids: [notification.id], changes });
    }

    function updateUnreadCount() {
        totalUnreadCount.value = notifications.value.filter((n) => !n.seen_time).length;
    }

    return {
        notifications,
        totalUnreadCount,
        unreadNotifications,
        loadingNotifications,
        updateNotification,
        updateBatchNotification,
        startWatchingNotifications,
        stopWatchingNotifications,
    };
});

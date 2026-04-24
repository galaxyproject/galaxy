import { defineStore } from "pinia";
import { computed, ref, watch } from "vue";

import { GalaxyApi } from "@/api";
import type { NotificationChanges, UserNotification, UserNotificationsBatchUpdateRequest } from "@/api/notifications";
import { useResourceWatcher } from "@/composables/resourceWatcher";
import { useSSE } from "@/composables/useNotificationSSE";
import { useConfigStore } from "@/stores/configurationStore";
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

    const unreadNotifications = computed(() => notifications.value.filter((n) => !n.seen_time));

    // --- SSE setup (listen only for notification event types) ---
    const NOTIFICATION_EVENT_TYPES = ["notification_update", "broadcast_update", "notification_status"] as const;
    const { connect: sseConnect, disconnect: sseDisconnect } = useSSE(handleSSEEvent, NOTIFICATION_EVENT_TYPES);
    let stopPolling: (() => void) | null = null;

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

    // Choose between SSE and polling based on the server config flag
    // `enable_notification_system`. The `/api/events/stream` endpoint accepts
    // connections regardless of the flag, so we cannot rely on EventSource
    // connectivity to decide — config is the source of truth.
    //
    // `useResourceWatcher` is instantiated lazily because it registers a
    // `visibilitychange` listener that calls `startWatchingResourceIfNeeded`
    // every time the tab regains focus — in SSE mode that would re-start
    // polling we explicitly don't want.
    let watchingInitialized = false;
    function ensureWatchingWithConfig() {
        if (watchingInitialized) {
            return;
        }
        watchingInitialized = true;

        const configStore = useConfigStore();
        const decide = () => {
            if (configStore.config?.enable_notification_system) {
                sseConnect();
            } else {
                const { startWatchingResource: startPolling, stopWatchingResource } = useResourceWatcher(
                    getNotificationStatus,
                    {
                        shortPollingInterval: ACTIVE_POLLING_INTERVAL,
                        longPollingInterval: INACTIVE_POLLING_INTERVAL,
                    },
                );
                stopPolling = stopWatchingResource;
                startPolling();
            }
        };

        if (configStore.isLoaded) {
            decide();
        } else {
            const stop = watch(
                () => configStore.isLoaded,
                (loaded) => {
                    if (loaded) {
                        stop();
                        decide();
                    }
                },
            );
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

        ensureWatchingWithConfig();
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
        // If the notification system (and therefore SSE) is disabled, trigger
        // a poll to refresh state after a local mutation.
        if (!useConfigStore().config?.enable_notification_system) {
            startWatchingNotifications();
        }
    }

    async function updateNotification(notification: UserNotification, changes: NotificationChanges) {
        return updateBatchNotification({ notification_ids: [notification.id], changes });
    }

    function updateUnreadCount() {
        totalUnreadCount.value = notifications.value.filter((n) => !n.seen_time).length;
    }

    // Closes the SSE stream and stops the polling watcher so nothing running
    // in the background can outlive a full-page navigation (login/register).
    // A late-arriving response from an anonymous-cookie request would otherwise
    // overwrite the just-issued authenticated ``galaxysession`` cookie.
    function stopWatchingNotifications() {
        sseDisconnect();
        if (stopPolling) {
            stopPolling();
            stopPolling = null;
        }
        watchingInitialized = false;
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

import { defineStore } from "pinia";
import { computed, ref } from "vue";

import {
    loadNotificationsFromServer,
    loadNotificationsStatus,
    type NotificationChanges,
    updateBatchNotificationsOnServer,
    type UserNotification,
    type UserNotificationsBatchUpdateRequest,
} from "@/api/notifications";
import { useResourceWatcher } from "@/composables/resourceWatcher";
import { mergeObjectListsById } from "@/utils/utils";

import { useBroadcastsStore } from "./broadcastsStore";

const ACTIVE_POLLING_INTERVAL = 30000; // 30 seconds
const INACTIVE_POLLING_INTERVAL = ACTIVE_POLLING_INTERVAL * 20; // 10 minutes

export const useNotificationsStore = defineStore("notificationsStore", () => {
    const { startWatchingResource: startWatchingNotifications } = useResourceWatcher(getNotificationStatus, {
        shortPollingInterval: ACTIVE_POLLING_INTERVAL,
        longPollingInterval: INACTIVE_POLLING_INTERVAL,
    });
    const broadcastsStore = useBroadcastsStore();

    const totalUnreadCount = ref<number>(0);
    const notifications = ref<UserNotification[]>([]);

    const loadingNotifications = ref<boolean>(false);
    const lastNotificationUpdate = ref<Date | null>(null);

    const unreadNotifications = computed(() => notifications.value.filter((n) => !n.seen_time));

    async function loadNotifications() {
        const data = await loadNotificationsFromServer();
        notifications.value = mergeObjectListsById(data, [], "create_time", "desc");
    }

    async function getNotificationStatus() {
        try {
            if (!lastNotificationUpdate.value) {
                loadingNotifications.value = true;
                await broadcastsStore.loadBroadcasts();
                await loadNotifications();
                updateUnreadCount();
            } else {
                const data = await loadNotificationsStatus(lastNotificationUpdate.value);
                totalUnreadCount.value = data.total_unread_count;
                notifications.value = mergeObjectListsById(
                    notifications.value,
                    data.notifications as UserNotification[],
                    "create_time",
                    "desc"
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

    async function updateBatchNotification(request: UserNotificationsBatchUpdateRequest) {
        await updateBatchNotificationsOnServer(request);
        if (request.changes.deleted) {
            notifications.value = notifications.value.filter((n) => !request.notification_ids.includes(n.id));
        }
        startWatchingNotifications();
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
    };
});

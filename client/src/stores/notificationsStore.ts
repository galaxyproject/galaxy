import { computed, ref } from "vue";
import { defineStore } from "pinia";
import type { components } from "@/schema";
import { mergeObjectListsById } from "@/utils/utils";
import {
    loadNotificationsFromServer,
    loadNotificationsStatus,
    updateBatchNotificationsOnServer,
} from "@/stores/services/notifications.service";
import { useBroadcastsStore } from "./broadcastsStore";
import type { UserNotification } from "@/components/Notifications";

type NotificationChanges = components["schemas"]["UserNotificationUpdateRequest"];
type UserNotificationsBatchUpdateRequest = components["schemas"]["UserNotificationsBatchUpdateRequest"];

const STATUS_POLLING_DELAY = 5000;

export const useNotificationsStore = defineStore("notificationsStore", () => {
    const broadcastsStore = useBroadcastsStore();

    const totalUnreadCount = ref<number>(0);
    const notifications = ref<UserNotification[]>([]);

    const pollId = ref<any>(null);
    const loadingNotifications = ref<boolean>(false);
    const lastNotificationUpdate = ref<Date | null>(null);

    const unreadNotifications = computed(() => notifications.value.filter((n) => !n.seen_time));

    async function loadNotifications() {
        await loadNotificationsFromServer().then((data) => {
            notifications.value = mergeObjectListsById(data, [], "create_time", "desc");
        });
    }

    async function getNotificationStatus() {
        stopPollingNotifications();
        try {
            if (!lastNotificationUpdate.value) {
                loadingNotifications.value = true;
                await broadcastsStore.loadBroadcasts();
                await loadNotifications();
            } else {
                await loadNotificationsStatus(lastNotificationUpdate.value).then((data) => {
                    totalUnreadCount.value = data.total_unread_count;
                    notifications.value = mergeObjectListsById(
                        notifications.value,
                        data.notifications,
                        "create_time",
                        "desc"
                    );
                    broadcastsStore.updateBroadcasts(data.broadcasts);
                });
            }
            lastNotificationUpdate.value = new Date();
        } catch (e) {
            console.error(e);
        } finally {
            loadingNotifications.value = false;
        }
    }

    async function startPollingNotifications() {
        await getNotificationStatus();
        pollId.value = setTimeout(() => startPollingNotifications(), STATUS_POLLING_DELAY);
    }

    function stopPollingNotifications() {
        pollId.value = clearTimeout(pollId.value);
    }

    async function updateBatchNotification(request: UserNotificationsBatchUpdateRequest) {
        await updateBatchNotificationsOnServer(request);
        if (request.changes.deleted) {
            notifications.value = notifications.value.filter((n) => !request.notification_ids.includes(n.id));
        }
        await startPollingNotifications();
    }

    async function updateNotification(notification: UserNotification, changes: NotificationChanges) {
        return updateBatchNotification({ notification_ids: [notification.id], changes });
    }

    return {
        notifications,
        totalUnreadCount,
        unreadNotifications,
        loadingNotifications,
        updateNotification,
        updateBatchNotification,
        startPollingNotifications,
    };
});

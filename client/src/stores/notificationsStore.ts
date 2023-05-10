import { computed, ref } from "vue";
import { defineStore } from "pinia";
import type { components } from "@/schema";
import { mergeObjectListsById } from "@/utils/utils";
import {
    loadNotificationsFromServer,
    loadNotificationsStatus,
    updateBatchNotificationsOnServer,
} from "@/stores/services/notifications.service";

type UserNotificationListResponse = components["schemas"]["UserNotificationListResponse"];
type UserNotificationsBatchUpdateRequest = components["schemas"]["UserNotificationsBatchUpdateRequest"];

export const useNotificationsStore = defineStore("notificationsStore", () => {
    const totalUnreadCount = ref<number>(0);
    const notifications = ref<UserNotificationListResponse>([]);

    const pollId = ref<any>(null);
    const loadingNotifications = ref<boolean>(false);
    const lastNotificationPoll = ref<Date | null>(null);

    const unreadNotifications = computed(() => notifications.value.filter((n) => !n.seen_time));
    const favoriteNotifications = computed(() => notifications.value.filter((item) => item.favorite));

    async function loadNotifications() {
        await loadNotificationsFromServer().then((data) => {
            notifications.value = mergeObjectListsById(data, [], "create_time", "desc");
        });
    }

    async function getNotificationStatus() {
        stopPollingNotifications();
        if (!lastNotificationPoll.value) {
            loadingNotifications.value = true;
            await loadNotifications();
            lastNotificationPoll.value = new Date();
        } else {
            await loadNotificationsStatus(lastNotificationPoll.value).then((data) => {
                totalUnreadCount.value = data.total_unread_count;
                notifications.value = mergeObjectListsById(
                    notifications.value,
                    data.notifications,
                    "create_time",
                    "desc"
                );
                lastNotificationPoll.value = new Date();
            });
        }
        loadingNotifications.value = false;
    }

    async function startPollingNotifications() {
        await getNotificationStatus();
        pollId.value = setTimeout(() => startPollingNotifications(), 1000);
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

    return {
        notifications,
        totalUnreadCount,
        unreadNotifications,
        loadingNotifications,
        favoriteNotifications,
        updateBatchNotification,
        startPollingNotifications,
    };
});

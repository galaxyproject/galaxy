import { defineStore } from "pinia";
import { computed, ref, set } from "vue";

import { fetchAllBroadcasts } from "@/api/notifications.broadcast";
import { type components } from "@/api/schema";
import { useUserLocalStorage } from "@/composables/userLocalStorage";
import { mergeObjectListsById } from "@/utils/utils";

export type BroadcastNotification = components["schemas"]["BroadcastNotificationResponse"];
type Expirable = Pick<BroadcastNotification, "expiration_time">;

export const useBroadcastsStore = defineStore("broadcastsStore", () => {
    const broadcasts = ref<BroadcastNotification[]>([]);

    const loadingBroadcasts = ref<boolean>(false);
    const dismissedBroadcasts = useUserLocalStorage<{ [key: string]: Expirable }>("dismissed-broadcasts", {});

    const activeBroadcasts = computed(() => {
        return broadcasts.value.filter(isActive);
    });

    async function loadBroadcasts() {
        loadingBroadcasts.value = true;
        await fetchAllBroadcasts()
            .then((data) => {
                broadcasts.value = mergeObjectListsById(data, [], "create_time", "desc");
            })
            .finally(() => {
                loadingBroadcasts.value = false;
            });
    }

    function updateBroadcasts(broadcastList: BroadcastNotification[]) {
        broadcasts.value = mergeObjectListsById(broadcasts.value, broadcastList, "create_time", "desc").filter(
            (b) => !hasExpired(b.expiration_time)
        );
    }

    function dismissBroadcast(broadcast: BroadcastNotification) {
        set(dismissedBroadcasts.value, broadcast.id, { expiration_time: broadcast.expiration_time });
    }

    function hasExpired(expirationTimeStr?: string | null) {
        if (!expirationTimeStr) {
            return false;
        }
        const expirationTime = new Date(`${expirationTimeStr}Z`);
        const now = new Date();
        return now > expirationTime;
    }

    function isActive(broadcast: BroadcastNotification) {
        return (
            !dismissedBroadcasts.value[broadcast.id] &&
            !hasExpired(broadcast.expiration_time) &&
            hasBeenPublished(broadcast)
        );
    }

    function hasBeenPublished(broadcast: BroadcastNotification) {
        const publicationTime = new Date(`${broadcast.publication_time}Z`);
        const now = new Date();
        return now >= publicationTime;
    }

    function clearExpiredDismissedBroadcasts() {
        for (const key in dismissedBroadcasts.value) {
            if (hasExpired(dismissedBroadcasts.value[key]?.expiration_time)) {
                delete dismissedBroadcasts.value[key];
            }
        }
    }

    clearExpiredDismissedBroadcasts();

    return {
        broadcasts,
        dismissedBroadcasts,
        loadingBroadcasts,
        activeBroadcasts,
        dismissBroadcast,
        loadBroadcasts,
        updateBroadcasts,
    };
});

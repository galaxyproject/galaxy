import { computed, ref } from "vue";
import { defineStore } from "pinia";
import type { components } from "@/schema";
import { mergeObjectListsById } from "@/utils/utils";
import { loadBroadcastsFromServer } from "@/stores/services/broadcasts.service";

type BroadcastNotificationResponse = components["schemas"]["BroadcastNotificationResponse"];
type BroadcastNotificationListResponse = components["schemas"]["BroadcastNotificationListResponse"];

export const useBroadcastsStore = defineStore(
    "broadcastsStore",
    () => {
        const broadcasts = ref<BroadcastNotificationListResponse>([]);

        const pollId = ref<any>(null);
        const loadingBroadcasts = ref<boolean>(false);
        const seenBroadcasts = ref<{ id: string; seen_time: string }[]>([]);

        const notSeenBroadcasts = computed(() => {
            return broadcasts.value.filter((b) => !seenBroadcasts.value.find((s) => s.id === b.id));
        });

        async function loadBroadcasts() {
            stopPollingBroadcasts();
            loadingBroadcasts.value = true;
            await loadBroadcastsFromServer()
                .then((data) => {
                    broadcasts.value = mergeObjectListsById(data, [], "create_time", "desc");
                })
                .finally(() => {
                    loadingBroadcasts.value = false;
                });
        }

        async function startPollingBroadcasts() {
            await loadBroadcasts();
            pollId.value = setTimeout(() => startPollingBroadcasts(), 60000);
        }

        function stopPollingBroadcasts() {
            pollId.value = clearTimeout(pollId.value);
        }

        function markBroadcastSeen(broadcast: BroadcastNotificationResponse) {
            seenBroadcasts.value.push({ id: broadcast.id, seen_time: broadcast.create_time });
        }

        function clearOldSeenBroadcasts() {
            const oneMonthAgo = new Date();
            oneMonthAgo.setMonth(oneMonthAgo.getMonth() - 1);
            const seenBroadcastsCopy = [...seenBroadcasts.value];
            for (const seenBroadcast of seenBroadcastsCopy) {
                if (new Date(seenBroadcast.seen_time) < oneMonthAgo) {
                    seenBroadcasts.value = seenBroadcasts.value.filter((b) => b.id !== seenBroadcast.id);
                }
            }
        }

        clearOldSeenBroadcasts();

        return {
            broadcasts,
            seenBroadcasts,
            loadingBroadcasts,
            notSeenBroadcasts,
            markBroadcastSeen,
            startPollingBroadcasts,
        };
    },
    {
        persist: {
            paths: ["seenBroadcasts"],
        },
    }
);

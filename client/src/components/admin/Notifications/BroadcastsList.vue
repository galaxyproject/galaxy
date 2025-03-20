<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCheck, faClock, faHourglassHalf, faRedo } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton, BCol, BRow } from "bootstrap-vue";
import { computed, ref } from "vue";
import { useRouter } from "vue-router/composables";

import { fetchAllBroadcasts, updateBroadcast } from "@/api/notifications.broadcast";
import { Toast } from "@/composables/toast";
import { type BroadcastNotification } from "@/stores/broadcastsStore";

import BroadcastCard from "./BroadcastCard.vue";
import Heading from "@/components/Common/Heading.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

library.add(faCheck, faClock, faHourglassHalf, faRedo);

const router = useRouter();

const overlay = ref(false);
const loading = ref(false);
const showActive = ref(true);
const showExpired = ref(true);
const showScheduled = ref(true);
const broadcasts = ref<BroadcastNotification[]>([]);

const filteredBroadcasts = computed(() => {
    return broadcasts.value.filter(filterBroadcasts);
});

const broadcastExpired = (item: BroadcastNotification) =>
    item.expiration_time && new Date(item.expiration_time) < new Date();

function filterBroadcasts(item: BroadcastNotification) {
    if (broadcastExpired(item)) {
        return showExpired.value;
    }
    if (broadcastPublished(item)) {
        return showActive.value;
    }
    return showScheduled.value;
}

function broadcastPublished(item: BroadcastNotification) {
    return new Date(item.publication_time) < new Date();
}

function onEdit(item: BroadcastNotification) {
    router.push(`/admin/notifications/edit_broadcast/${item.id}`);
}

async function onForceExpire(item: BroadcastNotification) {
    await updateBroadcast(item.id, { expiration_time: new Date().toISOString().slice(0, 23) });
    await loadBroadcastsList(true);
    Toast.info("Broadcast marked as expired. It will be removed from the database in the next cleanup cycle.");
}

function onGoToLink(link: string) {
    if (link.startsWith("/")) {
        router.push(link);
    } else {
        window.open(link, "_blank");
    }
}

async function loadBroadcastsList(overlayLoading = false) {
    if (overlayLoading) {
        overlay.value = true;
    } else {
        loading.value = true;
    }

    try {
        broadcasts.value = await fetchAllBroadcasts();
        broadcasts.value.sort((a, b) => new Date(b.create_time).getTime() - new Date(a.create_time).getTime());
    } finally {
        loading.value = false;
        overlay.value = false;
    }
}

loadBroadcastsList();
</script>

<template>
    <div>
        <Heading h2 class="mb-2"> Broadcasts list </Heading>
        <p v-localize class="mb-2">
            Broadcasts are notifications that are displayed to all users. They can be scheduled to be published at a
            specific time and can be set to expire at a specific time. They can also be marked as urgent to make them
            stand out.
        </p>
        <p class="mb-2">
            <b>NOTE:</b> Expired broadcasts are completely removed from the database in a periodic cleanup process. The
            cleanup interval is defined in the Galaxy configuration file under the
            <code>expired_notifications_cleanup_interval</code> key.
        </p>

        <div class="list-operations mb-2">
            <BRow class="align-items-center" no-gutters>
                <BCol class="ml-2">
                    <BRow align-h="start" align-v="center">
                        <span class="mx-2"> Filters: </span>
                        <BButtonGroup>
                            <BButton
                                id="show-active-filter-button"
                                size="sm"
                                :pressed="showActive"
                                title="Show active broadcasts"
                                variant="outline-primary"
                                @click="showActive = !showActive">
                                <FontAwesomeIcon :icon="faCheck" />
                                Active
                            </BButton>
                            <BButton
                                id="show-scheduled-filter-button"
                                size="sm"
                                :pressed="showScheduled"
                                title="Show scheduled broadcasts"
                                variant="outline-primary"
                                @click="showScheduled = !showScheduled">
                                <FontAwesomeIcon :icon="faClock" />
                                Scheduled
                            </BButton>
                            <BButton
                                id="show-expired-filter-button"
                                size="sm"
                                :pressed="showExpired"
                                title="Show expired broadcasts"
                                variant="outline-primary"
                                @click="showExpired = !showExpired">
                                <FontAwesomeIcon :icon="faHourglassHalf" />
                                Expired
                            </BButton>
                        </BButtonGroup>
                    </BRow>
                </BCol>
                <BCol>
                    <BRow align-h="end" align-v="center" no-gutters>
                        <BButton
                            v-b-tooltip.hover
                            size="sm"
                            :disabled="loading || overlay"
                            variant="outline-primary"
                            title="Refresh broadcasts"
                            @click="loadBroadcastsList">
                            <FontAwesomeIcon :icon="faRedo" />
                        </BButton>
                    </BRow>
                </BCol>
            </BRow>
        </div>

        <BAlert v-if="loading" variant="info" show>
            <LoadingSpan message="Loading broadcasts" />
        </BAlert>

        <BAlert v-else-if="filteredBroadcasts.length === 0" id="empty-broadcast-list-alert" variant="info" show>
            There are no broadcast notifications to show. Use the button above to create a new broadcast notification or
            change the filters.
        </BAlert>
        <BOverlay v-else :show="overlay" rounded="sm">
            <BroadcastCard
                v-for="notification in filteredBroadcasts"
                :key="notification.id"
                :broadcast-notification="notification"
                data-test-id="broadcast-item"
                @edit="onEdit"
                @expire="onForceExpire"
                @go-to-link="onGoToLink" />
        </BOverlay>
    </div>
</template>

<style scoped lang="scss">
@import "scss/theme/blue.scss";

.list-operations {
    border-radius: 0.5rem;
    border: 1px solid $gray-400;
    padding: 0.5rem;
}
</style>

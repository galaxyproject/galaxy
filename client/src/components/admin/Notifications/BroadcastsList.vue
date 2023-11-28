<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import {
    faBroadcastTower,
    faClock,
    faEdit,
    faHourglassHalf,
    faInfoCircle,
    faRedo,
    faTrash,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton, BCol, BInputGroup, BRow } from "bootstrap-vue";
import { computed, ref } from "vue";
import { useRouter } from "vue-router/composables";

import { fetchAllBroadcasts, updateBroadcast } from "@/api/notifications.broadcast";
import { useConfirmDialog } from "@/composables/confirmDialog";
import { useMarkdown } from "@/composables/markdown";
import { Toast } from "@/composables/toast";
import { BroadcastNotification } from "@/stores/broadcastsStore";

import Heading from "@/components/Common/Heading.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import UtcDate from "@/components/UtcDate.vue";

library.add(faBroadcastTower, faClock, faEdit, faHourglassHalf, faInfoCircle, faRedo, faTrash);

const router = useRouter();
const { confirm } = useConfirmDialog();
const { renderMarkdown } = useMarkdown({ openLinksInNewPage: true });

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

function getBroadcastVariant(item: BroadcastNotification) {
    switch (item.variant) {
        case "urgent":
            return "danger";
        default:
            return item.variant;
    }
}

function broadcastPublished(item: BroadcastNotification) {
    return new Date(item.publication_time) < new Date();
}

function onEditClick(item: BroadcastNotification) {
    router.push(`/admin/notifications/edit_broadcast/${item.id}`);
}

async function deleteBroadcast(item: BroadcastNotification) {
    const confirmed = await confirm("Are you sure you want to delete this broadcast?", "Delete broadcast");
    if (confirmed) {
        await updateBroadcast(item.id, { expiration_time: new Date().toISOString().slice(0, 23) });
        await loadBroadcastsList(true);
        Toast.info("Broadcast marked as expired and will be removed from the database");
    }
}

function getBroadcastPublicity(item: BroadcastNotification) {
    if (broadcastPublished(item)) {
        return `Published on ${new Date(item.publication_time + "Z").toLocaleString()}`;
    } else {
        return `Scheduled to publish on ${new Date(item.publication_time + "Z").toLocaleString()}`;
    }
}

function getBroadcastExpiry(item: BroadcastNotification) {
    if (item.expiration_time) {
        if (broadcastExpired(item)) {
            return `Expired on ${new Date(item.expiration_time + "Z").toLocaleString()}`;
        }
        return `Expires on ${new Date(item.expiration_time + "Z").toLocaleString()}`;
    } else {
        return "Does not expire";
    }
}

function onActionClick(item: BroadcastNotification, link: string) {
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
                                <FontAwesomeIcon icon="check" />
                                Active
                            </BButton>
                            <BButton
                                id="show-scheduled-filter-button"
                                size="sm"
                                :pressed="showScheduled"
                                title="Show scheduled broadcasts"
                                variant="outline-primary"
                                @click="showScheduled = !showScheduled">
                                <FontAwesomeIcon icon="clock" />
                                Scheduled
                            </BButton>
                            <BButton
                                id="show-expired-filter-button"
                                size="sm"
                                :pressed="showExpired"
                                title="Show expired broadcasts"
                                variant="outline-primary"
                                @click="showExpired = !showExpired">
                                <FontAwesomeIcon icon="hourglass-half" />
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
            No broadcasts to show. Use the button above to create a new broadcast. Or change the filters.
        </BAlert>

        <BOverlay v-else :show="overlay" rounded="sm">
            <div v-for="broadcast in filteredBroadcasts" :key="broadcast.id" class="broadcast-card mb-2">
                <BRow align-v="center" align-h="between" no-gutters>
                    <Heading size="md" class="mb-0" :class="broadcastExpired(broadcast) ? 'expired-broadcast' : ''">
                        <FontAwesomeIcon :class="`text-${getBroadcastVariant(broadcast)}`" :icon="faInfoCircle" />
                        {{ broadcast.content.subject }}
                    </Heading>

                    <BRow align-h="end" align-v="center" no-gutters>
                        <span>
                            created
                            <UtcDate class="mr-2" :date="broadcast.create_time" mode="elapsed" />
                        </span>

                        <BInputGroup v-if="!broadcastExpired(broadcast)">
                            <BButton
                                id="edit-broadcast-button"
                                v-b-tooltip.hover
                                variant="link"
                                title="Edit broadcast"
                                @click="onEditClick(broadcast)">
                                <FontAwesomeIcon :icon="faEdit" />
                            </BButton>

                            <BButton
                                id="delete-button"
                                v-b-tooltip.hover
                                variant="link"
                                title="Delete broadcast"
                                @click="() => deleteBroadcast(broadcast)">
                                <FontAwesomeIcon icon="trash" />
                            </BButton>
                        </BInputGroup>
                    </BRow>
                </BRow>

                <BRow align-v="center" align-h="between" no-gutters>
                    <BCol cols="auto">
                        <BRow align-v="center" no-gutters>
                            <span
                                :class="broadcastExpired(broadcast) ? 'expired-broadcast' : ''"
                                v-html="renderMarkdown(broadcast.content.message)" />
                        </BRow>

                        <BRow no-gutters>
                            <BButton
                                v-for="actionLink in broadcast.content.action_links"
                                :key="actionLink.action_name"
                                class="mr-1"
                                :title="actionLink.action_name"
                                variant="primary"
                                @click="onActionClick(broadcast, actionLink.link)">
                                {{ actionLink.action_name }}
                            </BButton>
                        </BRow>
                    </BCol>

                    <BCol>
                        <BRow align-v="center" align-h="end" no-gutters>
                            <FontAwesomeIcon
                                :icon="broadcastPublished(broadcast) ? faBroadcastTower : faClock"
                                :class="broadcastPublished(broadcast) ? 'published' : 'scheduled'"
                                class="mx-1" />
                            {{ getBroadcastPublicity(broadcast) }}
                        </BRow>

                        <BRow align-v="center" align-h="end" no-gutters>
                            <FontAwesomeIcon
                                variant="danger"
                                :icon="broadcastExpired(broadcast) ? faTrash : faHourglassHalf"
                                :class="broadcastExpired(broadcast) ? 'expired' : 'expires'"
                                class="mx-1" />
                            {{ getBroadcastExpiry(broadcast) }}
                        </BRow>
                    </BCol>
                </BRow>
            </div>
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

.broadcast-card {
    border-radius: 0.25rem;
    border: 1px solid $gray-300;
    padding: 1rem;

    .expired-broadcast {
        text-decoration: line-through;
    }

    .published {
        color: $brand-primary;
    }

    .scheduled {
        color: $brand-warning;
    }

    .expires {
        color: $brand-info;
    }

    .expired {
        color: $brand-danger;
    }
}
</style>

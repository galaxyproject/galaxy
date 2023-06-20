<script setup lang="ts">
import { ref } from "vue";
import { type components } from "@/schema";
import { Toast } from "@/composables/toast";
import UtcDate from "@/components/UtcDate.vue";
import { useRouter } from "vue-router/composables";
import { useMarkdown } from "@/composables/markdown";
import Heading from "@/components/Common/Heading.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import { library } from "@fortawesome/fontawesome-svg-core";
import { useConfirmDialog } from "@/composables/confirmDialog";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BroadcastNotification } from "@/stores/broadcastsStore";
import { loadBroadcasts, updateBroadcast } from "@/components/admin/Notifications/broadcasts.services";
import { faBroadcastTower, faClock, faEdit, faHourglassHalf, faInfoCircle } from "@fortawesome/free-solid-svg-icons";

library.add(faBroadcastTower, faClock, faEdit, faHourglassHalf, faInfoCircle);

type BroadcastNotificationResponse = components["schemas"]["BroadcastNotificationResponse"];

const router = useRouter();
const { confirm } = useConfirmDialog();
const { renderMarkdown } = useMarkdown({ openLinksInNewPage: true });

const loadingBroadcasts = ref(false);
const broadcasts = ref<BroadcastNotificationResponse[]>([]);

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
        await loadBroadcastsList();
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

async function loadBroadcastsList() {
    loadingBroadcasts.value = true;
    broadcasts.value = await loadBroadcasts();
    broadcasts.value.sort((a, b) => new Date(b.create_time).getTime() - new Date(a.create_time).getTime());
    loadingBroadcasts.value = false;
}
loadBroadcastsList();
</script>

<template>
    <div>
        <Heading size="md" class="mb-2"> Broadcasts list </Heading>

        <BAlert v-if="loadingBroadcasts" variant="info" show>
            <LoadingSpan message="Loading broadcasts" />
        </BAlert>

        <BAlert v-else-if="broadcasts.length === 0" variant="info" show>
            No broadcasts to show. Use the button above to create a new broadcast.
        </BAlert>

        <div v-else class="mx-1">
            <BCard v-for="broadcast in broadcasts" :key="broadcast.id" class="mb-2">
                <BRow align-v="center" align-h="between" class="mb-0 mx-0">
                    <Heading size="md" class="mb-0">
                        <FontAwesomeIcon :class="`text-${getBroadcastVariant(broadcast)}`" :icon="faInfoCircle" />
                        {{ broadcast.content.subject }}
                    </Heading>
                    <BRow align-h="end" align-v="center">
                        <UtcDate class="mx-2" :date="broadcast.create_time" mode="elapsed" />
                        <BInputGroup>
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

                <BRow align-v="center" align-h="between" class="mx-0">
                    <BCol>
                        <BRow align-v="center">
                            <span class="broadcast-message" v-html="renderMarkdown(broadcast.content.message)" />
                        </BRow>
                        <BRow>
                            <BButton
                                v-for="actionLink in broadcast.content.action_links"
                                :key="actionLink.action_name"
                                class="mx-1"
                                :title="actionLink.action_name"
                                variant="primary"
                                @click="onActionClick(broadcast, actionLink.link)">
                                {{ actionLink.action_name }}
                            </BButton>
                        </BRow>
                    </BCol>
                    <BCol>
                        <BRow align-v="center" align-h="end">
                            <FontAwesomeIcon
                                :icon="broadcastPublished(broadcast) ? faBroadcastTower : faClock"
                                :class="broadcastPublished(broadcast) ? 'published' : 'scheduled'"
                                class="mx-1" />
                            {{ getBroadcastPublicity(broadcast) }}
                        </BRow>
                        <BRow align-v="center" align-h="end">
                            <FontAwesomeIcon :icon="faHourglassHalf" class="mx-1 expire" />
                            {{ getBroadcastExpiry(broadcast) }}
                        </BRow>
                    </BCol>
                </BRow>
            </BCard>
        </div>
    </div>
</template>

<style scoped lang="scss">
@import "scss/theme/blue.scss";
.published {
    color: $brand-primary;
}

.scheduled {
    color: $brand-warning;
}

.expire {
    color: $brand-info;
}
</style>

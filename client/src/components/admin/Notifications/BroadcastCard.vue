<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import {
    faBroadcastTower,
    faClock,
    faEdit,
    faHourglassHalf,
    faInfoCircle,
    faTrash,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, BCol, BInputGroup, BRow } from "bootstrap-vue";
import { computed } from "vue";

import { useConfirmDialog } from "@/composables/confirmDialog";
import { useMarkdown } from "@/composables/markdown";
import { type BroadcastNotification } from "@/stores/broadcastsStore";

import Heading from "@/components/Common/Heading.vue";
import UtcDate from "@/components/UtcDate.vue";

library.add(faBroadcastTower, faClock, faEdit, faHourglassHalf, faInfoCircle, faTrash);

const { confirm } = useConfirmDialog();
const { renderMarkdown } = useMarkdown({ openLinksInNewPage: true });

interface Props {
    broadcastNotification: BroadcastNotification;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "edit", broadcastNotification: BroadcastNotification): void;
    (e: "expire", broadcastNotification: BroadcastNotification): void;
    (e: "go-to-link", link: string): void;
}>();

const notification = computed(() => props.broadcastNotification);

const hasExpired = computed(() => {
    return notification.value.expiration_time && new Date(notification.value.expiration_time) < new Date();
});

const hasBeenPublished = computed(() => {
    return new Date(notification.value.publication_time) < new Date();
});

const notificationVariant = computed(() => {
    switch (notification.value.variant) {
        case "urgent":
            return "danger";
        default:
            return notification.value.variant;
    }
});

const publicationTimePrefix = computed(() => {
    if (hasBeenPublished.value) {
        return "Published";
    }
    return "Scheduled to be published";
});

const expirationTimePrefix = computed(() => {
    if (notification.value.expiration_time) {
        if (hasExpired.value) {
            return "Expired";
        }
        return "Expires";
    }
    return "Does not expire";
});

function onEditClick() {
    emit("edit", notification.value);
}

async function onForceExpirationClick() {
    const confirmed = await confirm(
        "Are you sure you want to expire this broadcast? It will be automatically deleted on the next cleanup cycle.",
        "Expire broadcast"
    );
    if (confirmed) {
        emit("expire", notification.value);
    }
}

function onActionClick(link: string) {
    emit("go-to-link", link);
}
</script>

<template>
    <div class="broadcast-card mb-2">
        <BRow align-v="center" align-h="between" no-gutters>
            <Heading size="md" class="mb-0" :class="hasExpired ? 'expired-broadcast' : ''">
                <FontAwesomeIcon :class="`text-${notificationVariant}`" :icon="faInfoCircle" />
                {{ notification.content.subject }}
            </Heading>

            <BRow align-h="end" align-v="center" no-gutters>
                <span>
                    created
                    <UtcDate class="mr-2" :date="notification.create_time" mode="elapsed" />
                </span>

                <BInputGroup v-if="!hasExpired">
                    <BButton
                        id="edit-broadcast-button"
                        v-b-tooltip.hover
                        variant="link"
                        title="Edit broadcast"
                        @click="onEditClick">
                        <FontAwesomeIcon :icon="faEdit" />
                    </BButton>

                    <BButton
                        id="delete-button"
                        v-b-tooltip.hover
                        variant="link"
                        title="Delete broadcast"
                        @click="onForceExpirationClick">
                        <FontAwesomeIcon :icon="faTrash" />
                    </BButton>
                </BInputGroup>
            </BRow>
        </BRow>

        <BRow align-v="center" align-h="between" no-gutters>
            <BCol cols="auto">
                <BRow align-v="center" no-gutters>
                    <span
                        :class="hasExpired ? 'expired-broadcast' : ''"
                        v-html="renderMarkdown(notification.content.message)" />
                </BRow>

                <BRow no-gutters>
                    <BButton
                        v-for="actionLink in notification.content.action_links"
                        :key="actionLink.action_name"
                        class="mr-1"
                        :title="actionLink.action_name"
                        variant="primary"
                        @click="onActionClick(actionLink.link)">
                        {{ actionLink.action_name }}
                    </BButton>
                </BRow>
            </BCol>

            <BCol>
                <BRow align-v="center" align-h="end" no-gutters>
                    <FontAwesomeIcon
                        :icon="hasBeenPublished ? faBroadcastTower : faClock"
                        :class="hasBeenPublished ? 'published' : 'scheduled'"
                        class="mx-1" />
                    {{ publicationTimePrefix }}
                    <UtcDate class="ml-1" :date="notification.publication_time" mode="elapsed" />
                </BRow>

                <BRow align-v="center" align-h="end" no-gutters>
                    <FontAwesomeIcon
                        variant="danger"
                        :icon="faHourglassHalf"
                        :class="hasExpired ? 'expired' : 'expires'"
                        class="mx-1" />
                    {{ expirationTimePrefix }}
                    <UtcDate
                        v-if="notification.expiration_time"
                        class="ml-1"
                        :date="notification.expiration_time"
                        mode="elapsed" />
                </BRow>
            </BCol>
        </BRow>
    </div>
</template>

<style scoped lang="scss">
@import "scss/theme/blue.scss";
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

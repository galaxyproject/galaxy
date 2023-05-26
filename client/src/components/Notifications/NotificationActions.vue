<script setup lang="ts">
import { formatDistanceToNow, parseISO } from "date-fns";
import { BInputGroup, BCol, BRow, BButton } from "bootstrap-vue";
import type { components } from "@/schema";
import UtcDate from "@/components/UtcDate.vue";
import { library } from "@fortawesome/fontawesome-svg-core";
import AsyncButton from "@/components/Common/AsyncButton.vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faHourglassHalf } from "@fortawesome/free-solid-svg-icons";
import { useNotificationsStore } from "@/stores/notificationsStore";

library.add(faHourglassHalf);

type UserNotification = components["schemas"]["UserNotificationResponse"];
type NotificationChanges = components["schemas"]["UserNotificationUpdateRequest"];

interface Props {
    notification: UserNotification;
}

defineProps<Props>();

const notificationsStore = useNotificationsStore();

async function updateNotification(notification: UserNotification, changes: NotificationChanges) {
    await notificationsStore.updateBatchNotification({ notification_ids: [notification.id], changes });
}

function getNotificationExpirationTitle(notification: UserNotification) {
    if (notification.favorite) {
        return "This notification will not be deleted automatically because it is marked as favorite";
    } else if (notification.expiration_time) {
        const expirationTime = parseISO(notification.expiration_time);
        return `This notification will be automatically deleted ${formatDistanceToNow(expirationTime, {
            addSuffix: true,
        })}`;
    }
}
</script>

<template>
    <BCol>
        <BRow align-h="end" align-v="center">
            <UtcDate class="mx-2" :date="notification.create_time" mode="elapsed" />
            <BInputGroup>
                <AsyncButton
                    v-if="!notification.seen_time"
                    title="Mark as read"
                    icon="check"
                    :action="() => updateNotification(notification, { seen: true })" />
                <BButton
                    v-else-if="notification.expiration_time"
                    v-b-tooltip.hover
                    variant="link"
                    :title="getNotificationExpirationTitle(notification)">
                    <FontAwesomeIcon icon="hourglass-half" />
                </BButton>
                <AsyncButton
                    v-if="notification.favorite"
                    title="Remove from favorites"
                    icon="star"
                    :action="() => updateNotification(notification, { favorite: false })" />
                <AsyncButton
                    v-else
                    title="Add to favorites"
                    icon="fa-regular fa-star"
                    :action="() => updateNotification(notification, { favorite: true })" />
                <AsyncButton
                    icon="trash"
                    title="Delete"
                    :action="() => updateNotification(notification, { deleted: true })" />
            </BInputGroup>
        </BRow>
    </BCol>
</template>

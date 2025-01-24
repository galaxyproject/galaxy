<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faHourglassHalf } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, BButtonGroup } from "bootstrap-vue";
import { formatDistanceToNow, parseISO } from "date-fns";

import type { UserNotification } from "@/api/notifications";
import { useNotificationsStore } from "@/stores/notificationsStore";

import AsyncButton from "@/components/Common/AsyncButton.vue";
import UtcDate from "@/components/UtcDate.vue";

library.add(faHourglassHalf);

interface Props {
    notification: UserNotification;
}

defineProps<Props>();

const notificationsStore = useNotificationsStore();

function getNotificationExpirationTitle(notification: UserNotification) {
    if (notification.expiration_time) {
        const expirationTime = parseISO(notification.expiration_time);
        return `This notification will be automatically deleted ${formatDistanceToNow(expirationTime, {
            addSuffix: true,
        })}`;
    } else {
        return "This notification will never be automatically deleted";
    }
}
</script>

<template>
    <div v-if="notification" class="notification-actions">
        <div class="notification-actions-body">
            <BBadge v-b-tooltip pill>
                <UtcDate :date="notification.publication_time ?? notification.create_time" mode="elapsed" />
            </BBadge>

            <BButtonGroup class="notification-actions-buttons">
                <AsyncButton
                    v-if="!notification.seen_time"
                    id="mark-as-read-button"
                    title="Mark as read"
                    icon="check"
                    size="sm"
                    class="inline-icon-button"
                    :action="() => notificationsStore.updateNotification(notification, { seen: true })" />

                <BButton
                    v-else-if="notification.expiration_time"
                    id="expiration-time-button"
                    v-b-tooltip.hover
                    variant="link"
                    size="sm"
                    class="inline-icon-button"
                    :title="getNotificationExpirationTitle(notification)">
                    <FontAwesomeIcon icon="hourglass-half" fixed-width />
                </BButton>

                <AsyncButton
                    id="delete-button"
                    icon="trash"
                    title="Delete"
                    size="sm"
                    class="inline-icon-button"
                    :action="() => notificationsStore.updateNotification(notification, { deleted: true })" />
            </BButtonGroup>
        </div>
    </div>
</template>

<style scoped lang="scss">
.notification-actions {
    @container notification-content (max-width: 576px) {
        grid-row: 3;
    }

    .notification-actions-body {
        display: flex;
        gap: 0.5rem;
        align-items: center;
        justify-content: space-between;

        .notification-actions-buttons {
            gap: 0.5rem;
        }
    }
}
</style>

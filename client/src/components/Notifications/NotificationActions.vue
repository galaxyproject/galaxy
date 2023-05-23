<script setup lang="ts">
import { parseISO } from "date-fns";
import Vue, { type PropType } from "vue";
import BootstrapVue from "bootstrap-vue";
import type { components } from "@/schema";
import UtcDate from "@/components/UtcDate.vue";
import { library } from "@fortawesome/fontawesome-svg-core";
import AsyncButton from "@/components/Common/AsyncButton.vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faHourglassHalf } from "@fortawesome/free-solid-svg-icons";
import { useNotificationsStore } from "@/stores/notificationsStore";

Vue.use(BootstrapVue);

// @ts-ignore
library.add(faHourglassHalf);

type UserNotificationResponse = components["schemas"]["UserNotificationResponse"];

defineProps({
    notification: {
        type: Object as PropType<UserNotificationResponse>,
        required: true,
    },
});

const notificationsStore = useNotificationsStore();

async function updateNotification(notification: UserNotificationResponse, changes: any) {
    await notificationsStore.updateBatchNotification({ notification_ids: [notification.id], changes });
}

function getNotificationExpirationTitle(notification: UserNotificationResponse) {
    if (notification.favorite) {
        return "This notification will not be deleted automatically because it is marked as favorite";
    } else if (notification.expiration_time) {
        let calcDiff = "";
        const expirationTime = parseISO(notification.expiration_time);
        const now = new Date();
        const diff = expirationTime.getTime() - now.getTime();
        const diffInMinutes = Math.round(diff / 1000 / 60);
        if (diffInMinutes < 60) {
            calcDiff = `${diffInMinutes} minutes`;
        } else {
            const diffInHours = Math.round(diffInMinutes / 60);
            if (diffInHours < 24) {
                calcDiff = `${diffInHours} hours`;
            } else {
                const diffInDays = Math.round(diffInHours / 24);
                calcDiff = `${diffInDays} days`;
            }
        }

        return `This notification will be deleted in ${calcDiff}`;
    } else {
        return "This notification will be deleted automatically";
    }
}
</script>

<template>
    <BCol>
        <BRow align-h="end" align-v="center">
            <UtcDate :date="notification.create_time" mode="elapsed" />
            <BInputGroup>
                <AsyncButton
                    v-if="!notification.seen_time"
                    title="Mark as read"
                    icon="check"
                    :action="() => updateNotification(notification, { seen: true })" />
                <BButton v-else v-b-tooltip.hover variant="link" :title="getNotificationExpirationTitle(notification)">
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

<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faExternalLinkAlt, faRetweet } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BLink } from "bootstrap-vue";
import { computed } from "vue";

import type { SharedItemNotification } from "@/api/notifications";
import { useNotificationsStore } from "@/stores/notificationsStore";
import { absPath } from "@/utils/redirect";
import { capitalizeFirstLetter } from "@/utils/strings";

import NotificationActions from "@/components/Notifications/NotificationActions.vue";

library.add(faExternalLinkAlt, faRetweet);

interface Props {
    notification: SharedItemNotification;
}

const props = defineProps<Props>();

const notificationsStore = useNotificationsStore();

const content = computed(() => props.notification.content);

const sharedItemType = computed(() => {
    if (content.value.item_type) {
        return capitalizeFirstLetter(content.value.item_type);
    } else {
        return "Item";
    }
});

const notificationVariant = computed(() => {
    switch (props.notification.variant) {
        case "urgent":
            return "danger";
        default:
            return props.notification.variant;
    }
});

const sharedItemUrl = computed(() => {
    return absPath(content.value.slug);
});

function markNotificationAsSeen() {
    notificationsStore.updateNotification(props.notification, { seen: true });
}
</script>

<template>
    <div class="notification-container">
        <div class="notification-header">
            <div :class="!props.notification.seen_time ? 'font-weight-bold' : ''" class="notification-title">
                <FontAwesomeIcon :class="`text-${notificationVariant}`" :icon="faRetweet" fixed-width size="sm" />
                {{ sharedItemType }}
                shared with you by <em>{{ content.owner_name }}</em>
            </div>
        </div>

        <NotificationActions class="notification-actions" :notification="notification" />

        <p id="notification-message" class="notification-message">
            <span>The user</span>
            <b>{{ content.owner_name }}</b>
            <span>shared </span>
            <BLink
                v-b-tooltip.bottom
                :title="`View ${content.item_type} in new tab`"
                class="text-primary"
                :href="sharedItemUrl"
                target="_blank"
                @click="markNotificationAsSeen()">
                {{ content.item_name }}
                <FontAwesomeIcon :icon="faExternalLinkAlt" fixed-width size="sm" />
            </BLink>
            <em>{{ content.item_type }}</em>
            <span> with you.</span>
        </p>
    </div>
</template>

<style scoped lang="scss">
@import "style.scss";
</style>

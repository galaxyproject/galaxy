<script setup lang="ts">
import { computed } from "vue";
import { BCol, BRow, BLink } from "bootstrap-vue";
import Heading from "@/components/Common/Heading.vue";
import { library } from "@fortawesome/fontawesome-svg-core";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { useNotificationsStore } from "@/stores/notificationsStore";
import { faExternalLinkAlt, faRetweet } from "@fortawesome/free-solid-svg-icons";
import NotificationActions from "@/components/Notifications/NotificationActions.vue";
import type { SharedItemNotification } from "@/components/Notifications";
import { absPath } from "@/utils/redirect";

library.add(faExternalLinkAlt, faRetweet);

interface Props {
    notification: SharedItemNotification;
}

const props = defineProps<Props>();

const notificationsStore = useNotificationsStore();

function capitalizeFirstLetter(string: string) {
    return string.charAt(0).toUpperCase() + string.slice(1);
}

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
    <BCol>
        <BRow align-v="center">
            <Heading size="md" :bold="!notification.seen_time" class="mb-0">
                <FontAwesomeIcon :class="`text-${notificationVariant}`" icon="retweet" />
                {{ sharedItemType }} shared with you by <em>{{ content.owner_name }}</em>
            </Heading>
            <NotificationActions :notification="notification" />
        </BRow>
        <BRow>
            <p id="notification-message" class="m-0">
                <span>The user</span>
                <b>{{ content.owner_name }}</b>
                <span>shared </span>
                <b-link
                    v-b-tooltip.bottom
                    :title="`View ${content.item_type} in new tab`"
                    class="text-primary"
                    :href="sharedItemUrl"
                    target="_blank"
                    @click="markNotificationAsSeen()">
                    {{ content.item_name }}
                    <FontAwesomeIcon icon="external-link-alt" />
                </b-link>
                <em>{{ content.item_type }}</em>
                <span> with you.</span>
            </p>
        </BRow>
    </BCol>
</template>

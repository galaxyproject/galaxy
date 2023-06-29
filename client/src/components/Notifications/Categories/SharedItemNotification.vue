<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faExternalLinkAlt, faRetweet } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BCol, BRow, BLink } from "bootstrap-vue";
import { computed } from "vue";

import Heading from "@/components/Common/Heading.vue";
import type { SharedItemNotification } from "@/components/Notifications";
import NotificationActions from "@/components/Notifications/NotificationActions.vue";
import { useNotificationsStore } from "@/stores/notificationsStore";

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

function onClick(link: string) {
    notificationsStore.updateNotification(props.notification, { seen: true });
    window.open(link, "_blank");
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
                    @click="onClick(content.slug)">
                    {{ content.item_name }}
                    <FontAwesomeIcon icon="external-link-alt" />
                </b-link>
                <em>{{ content.item_type }}</em>
                <span> with you.</span>
            </p>
        </BRow>
    </BCol>
</template>

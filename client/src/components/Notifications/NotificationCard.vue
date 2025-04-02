<script setup lang="ts">
import {
    faCheck,
    faClock,
    faExternalLinkAlt,
    faHourglassHalf,
    faInbox,
    faRetweet,
    faTrash,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BLink } from "bootstrap-vue";
import { formatDistanceToNow, parseISO } from "date-fns";
import { computed } from "vue";

import { type UserNotification } from "@/api/notifications";
import { useMarkdown } from "@/composables/markdown";
import { useNotificationsStore } from "@/stores/notificationsStore";
import { absPath } from "@/utils/redirect";
import { capitalizeFirstLetter } from "@/utils/strings";

import GCard from "@/components/Common/GCard.vue";

const props = defineProps<{
    selected?: boolean;
    selectable?: boolean;
    unreadBorder?: boolean;
    notification: UserNotification;
}>();

const emit = defineEmits(["select"]);

const notificationsStore = useNotificationsStore();

const { renderMarkdown } = useMarkdown({ openLinksInNewPage: true });

const title = computed(() => {
    if (props.notification.category === "new_shared_item") {
        return `${sharedItemType.value} shared with you by ${props.notification.content.owner_name}`;
    } else {
        return props.notification.content.subject;
    }
});

const titleIcon = computed(() => {
    return {
        icon: props.notification.category === "new_shared_item" ? faRetweet : faInbox,
        class: `text-${notificationVariant.value}`,
    };
});

const sharedItemType = computed(() => {
    if (props.notification.category === "new_shared_item" && props.notification.content?.item_type) {
        return capitalizeFirstLetter(props.notification.content.item_type);
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

const primaryActions = computed(() => {
    const tmp = [
        {
            id: "expiration-time-button",
            label: "",
            title: props.notification?.expiration_time
                ? `This notification will be automatically deleted ${formatDistanceToNow(
                      parseISO(props.notification.expiration_time),
                      {
                          addSuffix: true,
                      }
                  )}`
                : "This notification will never be automatically deleted",
            icon: faHourglassHalf,
            size: "sm",
            class: "inline-icon-button",
            variant: "link",
            inline: true,
            visible: !!(props.notification.seen_time && props.notification.expiration_time),
        },
        {
            id: "delete-button",
            label: "",
            title: "Delete",
            icon: faTrash,
            size: "sm",
            class: "inline-icon-button",
            variant: "link",
            inline: true,
            handler: () => notificationsStore.updateNotification(props.notification, { deleted: true }),
            visible: !!props.notification.expiration_time,
        },
        {
            id: "mark-as-read-button",
            label: "",
            title: "Mark as read",
            icon: faCheck,
            size: "sm",
            class: "inline-icon-button",
            variant: "link",
            inline: true,
            handler: () => notificationsStore.updateNotification(props.notification, { seen: true }),
            visible: !props.notification.seen_time,
        },
    ];

    return tmp.filter((action) => action.visible);
});

function markNotificationAsSeen() {
    notificationsStore.updateNotification(props.notification, { seen: true });
}
</script>

<template>
    <GCard
        :id="props.notification.id"
        :title="title"
        :primary-actions="primaryActions"
        :title-size="'sm'"
        :title-icon="titleIcon"
        :selected="props.selected"
        :selectable="props.selectable"
        :update-time="props.notification.publication_time ?? props.notification.create_time"
        :update-time-icon="faClock"
        :update-time-title="`Sent ${props.notification.publication_time ? 'on' : 'at'}`"
        :content-class="[props.unreadBorder && !props.notification.seen_time ? 'border-dark unread-notification' : '']"
        @select="emit('select', [props.notification])">
        <template v-slot:description>
            <template v-if="props.notification.category === 'new_shared_item'">
                <span>The user</span>
                <b>{{ props.notification.content.owner_name }}</b>
                <span>shared </span>
                <BLink
                    v-b-tooltip.bottom
                    :title="`View ${props.notification.content.item_type} in new tab`"
                    class="text-primary"
                    :href="absPath(props.notification.content.slug)"
                    target="_blank"
                    @click="markNotificationAsSeen()">
                    {{ props.notification.content.item_name }}
                    <FontAwesomeIcon :icon="faExternalLinkAlt" fixed-width size="sm" />
                </BLink>
                <em>{{ props.notification.content.item_type }}</em>
                <span> with you.</span>
            </template>
            <template v-else>
                <span
                    id="notification-message"
                    class="notification-message"
                    v-html="renderMarkdown(props.notification.content.message)" />
            </template>
        </template>
    </GCard>
</template>

<style lang="scss">
.notification-message {
    p {
        margin: 0;
    }
}
</style>

<script setup lang="ts">
import {
    faCheck,
    faClock,
    faExternalLinkAlt,
    faHourglassHalf,
    faInbox,
    faRetweet,
    faTrash,
    faWrench,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BLink } from "bootstrap-vue";
import { formatDistanceToNow, parseISO } from "date-fns";
import { computed } from "vue";
import { useRouter } from "vue-router/composables";

import type { UserNotification } from "@/api/notifications";
import type { CardAction } from "@/components/Common/GCard.types";
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
const router = useRouter();

const { renderMarkdown } = useMarkdown({ openLinksInNewPage: false });

function handleMessageClick(event: MouseEvent) {
    const target = event.target as HTMLElement;
    const anchor = target.closest("a");

    if (anchor) {
        const href = anchor.getAttribute("href");
        if (href) {
            // Check if this is an internal link (same origin or relative path)
            try {
                const url = new URL(href, window.location.origin);
                if (url.origin === window.location.origin) {
                    event.preventDefault();
                    router.push(url.pathname + url.search + url.hash);
                }
            } catch {
                // If URL parsing fails, let the browser handle it
            }
        }
    }
}

const title = computed(() => {
    if (props.notification.category === "new_shared_item") {
        return `${sharedItemType.value} shared with you by ${props.notification.content.owner_name}`;
    } else if (props.notification.category === "tool_request") {
        return `Tool Request: ${props.notification.content.tool_name}`;
    } else {
        return props.notification.content.subject;
    }
});

const titleIcon = computed(() => {
    const iconMap: Record<string, unknown> = {
        new_shared_item: faRetweet,
        tool_request: faWrench,
    };
    return {
        icon: iconMap[props.notification.category] ?? faInbox,
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
    const tmp: CardAction[] = [
        {
            id: "expiration-time-button",
            label: "",
            title: props.notification?.expiration_time
                ? `This notification will be automatically deleted ${formatDistanceToNow(
                      parseISO(props.notification.expiration_time),
                      {
                          addSuffix: true,
                      },
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
        v-if="props.notification"
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
                <span>The user</span>{{ " " }}<b>{{ props.notification.content.owner_name }}</b
                >{{ " " }}<span>shared </span>
                <BLink
                    v-g-tooltip.bottom
                    :title="`View ${props.notification.content.item_type} in new tab`"
                    class="text-primary"
                    :href="absPath(props.notification.content.slug)"
                    target="_blank"
                    @click="markNotificationAsSeen()">
                    {{ props.notification.content.item_name }}
                    <FontAwesomeIcon :icon="faExternalLinkAlt" fixed-width size="sm" />
                </BLink>
                <em>{{ props.notification.content.item_type }}</em
                >{{ " " }}<span> with you.</span>
            </template>
            <template v-else-if="props.notification.category === 'tool_request'">
                <dl class="mb-0">
                    <template v-if="props.notification.content.description">
                        <dt>Description</dt>
                        <dd>{{ props.notification.content.description }}</dd>
                    </template>
                    <template v-if="props.notification.content.tool_url">
                        <dt>URL</dt>
                        <dd>
                            <BLink :href="props.notification.content.tool_url" target="_blank">
                                {{ props.notification.content.tool_url }}
                                <FontAwesomeIcon :icon="faExternalLinkAlt" fixed-width size="sm" />
                            </BLink>
                        </dd>
                    </template>
                    <template v-if="props.notification.content.scientific_domain">
                        <dt>Scientific domain</dt>
                        <dd>{{ props.notification.content.scientific_domain }}</dd>
                    </template>
                    <template v-if="props.notification.content.requested_version">
                        <dt>Version</dt>
                        <dd>{{ props.notification.content.requested_version }}</dd>
                    </template>
                    <template v-if="props.notification.content.requester_name">
                        <dt>Requested by</dt>
                        <dd>
                            {{ props.notification.content.requester_name }}
                            <span v-if="props.notification.content.requester_affiliation">
                                ({{ props.notification.content.requester_affiliation }})
                            </span>
                            <span v-if="props.notification.content.requester_email">
                                &mdash;
                                <BLink :href="`mailto:${props.notification.content.requester_email}`">
                                    {{ props.notification.content.requester_email }}
                                </BLink>
                            </span>
                        </dd>
                    </template>
                </dl>
            </template>
            <template v-else>
                <span
                    class="notification-message"
                    @click="handleMessageClick"
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

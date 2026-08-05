<script setup lang="ts">
import type { IconDefinition } from "@fortawesome/free-solid-svg-icons";
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

import type { RequestedTool, UserNotification } from "@/api/notifications";
import type { CardAction, TitleIcon } from "@/components/Common/GCard.types";
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

/** Display label for a requested tool: name, else shed id, else URL, else a placeholder. */
function toolLabel(tool: RequestedTool | undefined): string {
    return tool?.name || tool?.tool_shed_id || tool?.tool_url || "(unspecified)";
}

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
    } else if (props.notification.category === "storage_operation") {
        return props.notification.content.subject;
    } else if (props.notification.category === "tool_installation_request") {
        const tools = props.notification.content.tools;
        return tools.length === 1 && tools[0]
            ? `Tool Installation Request: ${toolLabel(tools[0])}`
            : `Tool Installation Request: ${tools.length} tools`;
    } else {
        return props.notification.content.subject;
    }
});

const titleIcon = computed<TitleIcon>(() => {
    const iconMap: Record<string, IconDefinition> = {
        new_shared_item: faRetweet,
        storage_operation: faHourglassHalf,
        tool_installation_request: faWrench,
    };
    return {
        icon: iconMap[props.notification.category] ?? faInbox,
        class: `text-${notificationVariant.value}`,
    };
});

/** The single requested tool, when a tool installation request contains exactly one. */
const singleRequestedTool = computed(() =>
    props.notification.category === "tool_installation_request" && props.notification.content.tools.length === 1
        ? props.notification.content.tools[0]
        : undefined,
);

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
    <div v-if="props.notification" :id="`notification-card-${props.notification.id}`">
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
            :content-class="[
                props.unreadBorder && !props.notification.seen_time ? 'border-dark unread-notification' : '',
            ]"
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
                <template v-else-if="props.notification.category === 'tool_installation_request'">
                    <dl class="mb-0">
                        <template v-if="props.notification.content.tools.length > 1">
                            <dt>Tools</dt>
                            <dd>
                                <ul class="mb-0 pl-3">
                                    <li v-for="(tool, index) in props.notification.content.tools" :key="index">
                                        {{ toolLabel(tool) }}
                                        <!-- Per-tool details nested under the tool so it is clear
                                             which tool each detail belongs to. -->
                                        <ul
                                            v-if="
                                                tool.tool_url ||
                                                tool.description ||
                                                tool.scientific_domain ||
                                                tool.requested_version
                                            "
                                            class="mb-0 pl-3 list-unstyled">
                                            <li v-if="tool.tool_url">
                                                <strong>URL:</strong>
                                                <span class="text-break">{{ tool.tool_url }}</span>
                                            </li>
                                            <li v-if="tool.description">
                                                <strong>Description:</strong> {{ tool.description }}
                                            </li>
                                            <li v-if="tool.scientific_domain">
                                                <strong>Scientific domain:</strong> {{ tool.scientific_domain }}
                                            </li>
                                            <li v-if="tool.requested_version">
                                                <strong>Version:</strong> {{ tool.requested_version }}
                                            </li>
                                        </ul>
                                    </li>
                                </ul>
                            </dd>
                        </template>
                        <template v-else>
                            <dt>Tool</dt>
                            <dd>{{ toolLabel(singleRequestedTool) }}</dd>
                        </template>
                        <template v-if="singleRequestedTool">
                            <template v-if="singleRequestedTool.tool_url">
                                <dt>URL</dt>
                                <dd>
                                    <span class="text-break">{{ singleRequestedTool.tool_url }}</span>
                                </dd>
                            </template>
                            <template v-if="singleRequestedTool.description">
                                <dt>Description</dt>
                                <dd>{{ singleRequestedTool.description }}</dd>
                            </template>
                            <template v-if="singleRequestedTool.scientific_domain">
                                <dt>Scientific domain</dt>
                                <dd>{{ singleRequestedTool.scientific_domain }}</dd>
                            </template>
                            <template v-if="singleRequestedTool.requested_version">
                                <dt>Version</dt>
                                <dd>{{ singleRequestedTool.requested_version }}</dd>
                            </template>
                        </template>
                        <template v-if="props.notification.content.workflow_id">
                            <dt>Workflow</dt>
                            <dd>
                                <RouterLink :to="`/workflows/run?id=${props.notification.content.workflow_id}`">
                                    {{ props.notification.content.workflow_id }}
                                </RouterLink>
                            </dd>
                        </template>
                        <template v-if="props.notification.content.additional_remarks">
                            <dt>Additional remarks</dt>
                            <dd>{{ props.notification.content.additional_remarks }}</dd>
                        </template>
                        <template v-if="props.notification.content.requester_email">
                            <dt>Requested by</dt>
                            <dd>
                                <BLink :href="`mailto:${props.notification.content.requester_email}`">
                                    {{ props.notification.content.requester_email }}
                                </BLink>
                            </dd>
                        </template>
                    </dl>
                </template>
                <template v-else-if="props.notification.category === 'storage_operation'">
                    <p>
                        {{ props.notification.content.message }}
                    </p>
                    <p class="mb-1">
                        <strong>Mode:</strong> {{ props.notification.content.mode }}
                        <span class="mx-2">|</span>
                        <strong>State:</strong> {{ props.notification.content.state }}
                    </p>
                    <p class="mb-1">
                        <strong>Total:</strong> {{ props.notification.content.total_count }}
                        <span class="mx-2">|</span>
                        <strong>Succeeded:</strong> {{ props.notification.content.succeeded_count }}
                        <span class="mx-2">|</span>
                        <strong>Failed:</strong> {{ props.notification.content.failed_count }}
                        <span class="mx-2">|</span>
                        <strong>Skipped:</strong> {{ props.notification.content.skipped_count }}
                    </p>
                    <BLink
                        class="text-primary"
                        :href="props.notification.content.run_url"
                        @click="markNotificationAsSeen()">
                        Open storage operation run status
                    </BLink>
                </template>
                <template v-else>
                    <span
                        class="notification-message"
                        @click="handleMessageClick"
                        v-html="renderMarkdown(props.notification.content.message)"></span>
                </template>
            </template>
        </GCard>
    </div>
</template>

<style lang="scss">
.notification-message {
    p {
        margin: 0;
    }
}
</style>

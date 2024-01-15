<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faInbox } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";

import { type MessageNotification } from "@/api/notifications";
import { useMarkdown } from "@/composables/markdown";

import NotificationActions from "@/components/Notifications/NotificationActions.vue";

library.add(faInbox);

type PartialNotification = Partial<MessageNotification> & { content: MessageNotification["content"] };

type Options =
    | {
          previewMode?: false;
          notification: MessageNotification;
      }
    | {
          previewMode: true;
          notification: PartialNotification;
      };

const props = defineProps<{
    options: Options;
}>();

const { renderMarkdown } = useMarkdown({ openLinksInNewPage: true });

const notificationVariant = computed(() => {
    switch (props.options.notification.variant) {
        case "urgent":
            return "danger";
        default:
            return props.options.notification.variant;
    }
});
</script>

<template>
    <div class="message-notification">
        <div class="message-notification-header">
            <div
                :class="!props.options.notification.seen_time ? 'font-weight-bold' : ''"
                class="message-notification-title">
                <FontAwesomeIcon :class="`text-${notificationVariant}`" icon="inbox" />
                {{ props.options.notification?.content?.subject }}
            </div>

            <NotificationActions v-if="!props.options.previewMode" :notification="props.options.notification" />
        </div>

        <div>
            <span id="notification-message" v-html="renderMarkdown(props.options.notification.content.message)" />
        </div>
    </div>
</template>

<style scoped lang="scss">
.message-notification {
    container: message-notification / inline-size;

    width: 100%;
    flex-grow: 1;

    .message-notification-title {
        font-size: 1rem;
    }

    @container message-notification (min-width: 576px) {
        .message-notification-header {
            display: flex;
            align-items: center;

            .message-notification-title {
                font-size: 1.25rem;
            }
        }
    }
}
</style>

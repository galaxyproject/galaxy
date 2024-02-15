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
    <div class="notification-container">
        <div class="notification-header">
            <div :class="!props.options.notification.seen_time ? 'font-weight-bold' : ''" class="notification-title">
                <FontAwesomeIcon :class="`text-${notificationVariant}`" :icon="faInbox" fixed-width size="sm" />
                {{ props.options.notification?.content?.subject }}
            </div>
        </div>

        <NotificationActions
            v-if="!props.options.previewMode"
            class="notification-actions"
            :notification="props.options.notification" />

        <span
            id="notification-message"
            class="notification-message"
            v-html="renderMarkdown(props.options.notification.content.message)" />
    </div>
</template>

<style scoped lang="scss">
@import "style.scss";
</style>

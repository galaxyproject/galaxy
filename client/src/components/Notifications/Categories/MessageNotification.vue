<script setup lang="ts">
import BootstrapVue from "bootstrap-vue";
import type { components } from "@/schema";
import Vue, { computed, type PropType } from "vue";
import Heading from "@/components/Common/Heading.vue";
import { faInbox } from "@fortawesome/free-solid-svg-icons";
import { library } from "@fortawesome/fontawesome-svg-core";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import NotificationActions from "@/components/Notifications/NotificationActions.vue";

Vue.use(BootstrapVue);

library.add(faInbox);

type UserNotificationResponse = components["schemas"]["UserNotificationResponse"];

const props = defineProps({
    notification: {
        type: Object as PropType<UserNotificationResponse>,
        required: true,
    },
});

const notificationVariant = computed(() => {
    switch (props.notification.variant) {
        case "urgent":
            return "danger";
        default:
            return props.notification.variant;
    }
});
</script>

<template>
    <BCol>
        <BRow align-v="center">
            <Heading size="md" :bold="!notification.seen_time" class="mb-0">
                <FontAwesomeIcon :class="`text-${notificationVariant}`" icon="inbox" />
                {{ notification.content.subject }}
            </Heading>
            <NotificationActions :notification="notification" />
        </BRow>
        <BRow>
            {{ notification.content.message }}
        </BRow>
    </BCol>
</template>

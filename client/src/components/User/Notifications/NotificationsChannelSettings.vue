<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faExclamationCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { ref, watch } from "vue";

import {
    type NotificationCategory,
    type NotificationChannel,
    type UserNotificationPreferences,
} from "@/api/notifications";
import { snakeCaseToTitleCase } from "@/utils/strings";

library.add(faExclamationCircle);

interface NotificationsChannelSettingsProps {
    preferences: UserNotificationPreferences;
    category: NotificationCategory;
    isCategoryEnabled: boolean;
    channel: NotificationChannel;
}

const props = defineProps<NotificationsChannelSettingsProps>();

const emit = defineEmits<{
    (event: "onChange", category: NotificationCategory, channel: NotificationChannel, value: boolean): void;
}>();

const value = ref<boolean>(props.preferences[props.category]!.channels[props.channel]);

watch(
    () => value.value,
    (newValue) => {
        emit("onChange", props.category, props.channel, newValue);
    }
);
</script>

<template>
    <div class="category-channel">
        <BFormCheckbox v-model="value" v-localize :disabled="!isCategoryEnabled">
            {{ snakeCaseToTitleCase(channel) }}
        </BFormCheckbox>

        <FontAwesomeIcon
            v-if="channel === 'push'"
            v-b-tooltip.hover="'Push notifications need to be enabled'"
            class="mx-2"
            :icon="faExclamationCircle" />
    </div>
</template>

<style scoped lang="scss">
.category-channel {
    display: flex;
    align-items: center;
}
</style>

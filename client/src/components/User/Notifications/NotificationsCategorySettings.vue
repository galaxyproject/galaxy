<script setup lang="ts">
import { computed, ref, watch } from "vue";

import {
    type NotificationCategory,
    type NotificationChannel,
    type UserNotificationPreferences,
} from "@/api/notifications";
import { snakeCaseToTitleCase } from "@/utils/strings";

import NotificationsChannelSettings from "./NotificationsChannelSettings.vue";

const categoryDescriptionMap: Record<NotificationCategory, string> = {
    message: `
        只有当 Galaxy 管理员向您发送消息时，您才会收到这些通知。
        请注意，对于某些关键或紧急的消息，即使您已禁用此通知渠道，您仍会收到通知。
    `,
    new_shared_item:
        "当有人与您共享一个项目（例如历史记录、工作流、可视化等）时，您将收到这些通知。",
};

interface NotificationsCategorySettingsProps {
    preferences: UserNotificationPreferences;
    supportedChannels: NotificationChannel[];
    category: NotificationCategory;
}

const props = defineProps<NotificationsCategorySettingsProps>();

const emit = defineEmits<{
    (event: "onCategoryEnabledChange", category: NotificationCategory, value: boolean): void;
    (event: "onChannelChange", category: NotificationCategory, channel: NotificationChannel, value: boolean): void;
}>();

const isCategoryEnabled = ref(props.preferences[props.category]!.enabled);
const checkBoxTitle = computed(() => (isCategoryEnabled.value ? "禁用通知" : "启用通知"));
const categoryDescription = computed(() => categoryDescriptionMap[props.category]);

watch(
    () => isCategoryEnabled.value,
    (newValue) => {
        emit("onCategoryEnabledChange", props.category, newValue);
    }
);

function onChannelChange(category: NotificationCategory, channel: NotificationChannel, value: boolean) {
    emit("onChannelChange", category, channel, value);
}
</script>

<template>
    <div>
        <div class="category-header">
            <BFormCheckbox v-model="isCategoryEnabled" v-b-tooltip.hover :title="checkBoxTitle" switch>
                <span v-localize class="category-title">{{ snakeCaseToTitleCase(category) }}</span>
            </BFormCheckbox>
        </div>

        <div v-if="categoryDescription" v-localize class="category-description">
            {{ categoryDescription }}
        </div>

        <div v-for="channel in supportedChannels" :key="channel">
            <NotificationsChannelSettings
                :preferences="preferences"
                :category="category"
                :is-category-enabled="isCategoryEnabled"
                :channel="channel"
                @onChange="onChannelChange" />
        </div>
    </div>
</template>

<style scoped lang="scss">
.category-header {
    gap: 1rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 0.5rem;
}

.category-title {
    font-weight: bold;
}

.category-description {
    font-size: 0.8rem;
    font-style: italic;
    margin-bottom: 0.5rem;
}
</style>

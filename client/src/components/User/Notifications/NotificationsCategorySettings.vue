<script setup lang="ts">
import { BFormCheckbox } from "bootstrap-vue";
import { computed, ref, watch } from "vue";

import type { NotificationCategory, NotificationChannel, UserNotificationPreferences } from "@/api/notifications";
import { snakeCaseToTitleCase } from "@/utils/strings";

import NotificationsChannelSettings from "./NotificationsChannelSettings.vue";

const categoryDescriptionMap: Partial<Record<NotificationCategory, string>> = {
    message: `
        You will receive these notifications only when your Galaxy administrators send you a message.
        Please note that for certain critical or urgent messages, you will receive notifications even if you have disabled this channel.
    `,
    new_shared_item:
        "You will receive these notifications when someone shares an item with you i.e. a history, workflow, visualization, etc.",
    tool_execution_completed:
        "Receive a notification when a tool run completes, with one summary for a collection. You can also change this preference on the tool form.",
    workflow_execution_completed:
        "Receive a notification when a workflow completes. You can also change this preference on the workflow run form.",
    storage_operation:
        "You will receive these notifications when a bulk storage operation completes (including failed outcomes).",
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
const checkBoxTitle = computed(() => (isCategoryEnabled.value ? "Disable notifications" : "Enable notifications"));
const categoryDescription = computed(() => categoryDescriptionMap[props.category]);

watch(
    () => isCategoryEnabled.value,
    (newValue) => {
        emit("onCategoryEnabledChange", props.category, newValue);
    },
);

function onChannelChange(category: NotificationCategory, channel: NotificationChannel, value: boolean) {
    emit("onChannelChange", category, channel, value);
}
</script>

<template>
    <div>
        <div class="category-header">
            <BFormCheckbox v-model="isCategoryEnabled" v-g-tooltip.hover :title="checkBoxTitle" switch>
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

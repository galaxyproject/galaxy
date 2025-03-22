<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCheckCircle, faExclamationCircle, faSave } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton } from "bootstrap-vue";
import { computed, ref, watch } from "vue";

import { GalaxyApi } from "@/api";
import {
    type NotificationCategory,
    type NotificationChannel,
    type UserNotificationPreferences,
} from "@/api/notifications";
import { useConfig } from "@/composables/config";
import { Toast } from "@/composables/toast";
import {
    browserSupportsPushNotifications,
    pushNotificationsEnabled,
    togglePushNotifications,
} from "@/composables/utils/pushNotifications";
import { errorMessageAsString } from "@/utils/simple-error";

import NotificationsCategorySettings from "./NotificationsCategorySettings.vue";
import AsyncButton from "@/components/Common/AsyncButton.vue";
import Heading from "@/components/Common/Heading.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

library.add(faCheckCircle, faExclamationCircle, faSave);

interface NotificationsPreferencesProps {
    embedded?: boolean;
    headerSize?: string;
}

const props = withDefaults(defineProps<NotificationsPreferencesProps>(), {
    embedded: true,
    headerSize: "h-lg",
});

const { config } = useConfig(true);

const loading = ref(false);
const errorMessage = ref<string | null>(null);
const pushNotificationsGranted = ref(pushNotificationsEnabled());
const notificationsPreferences = ref<UserNotificationPreferences>({});
const supportedChannels = ref<NotificationChannel[]>([]);

const categories = computed<NotificationCategory[]>(
    () => Object.keys(notificationsPreferences.value) as NotificationCategory[]
);
const showPreferences = computed(() => {
    return !loading.value && config.value.enable_notification_system && notificationsPreferences.value;
});

async function getNotificationsPreferences() {
    loading.value = true;
    try {
        const { response, data, error } = await GalaxyApi().GET("/api/notifications/preferences");

        if (error) {
            errorMessage.value = errorMessageAsString(error);
            return;
        }

        const serverSupportedChannels = response.headers.get("supported-channels")?.split(",") ?? [];
        supportedChannels.value = serverSupportedChannels as NotificationChannel[];
        notificationsPreferences.value = data.preferences;
    } finally {
        loading.value = false;
    }
}

async function updateNotificationsPreferences() {
    const { data, error } = await GalaxyApi().PUT("/api/notifications/preferences", {
        body: {
            preferences: notificationsPreferences.value,
        },
    });

    if (error) {
        errorMessage.value = errorMessageAsString(error);
        return;
    }

    notificationsPreferences.value = data.preferences;
    Toast.success("通知偏好更新成功");
}

async function onTogglePushNotifications() {
    pushNotificationsGranted.value = await togglePushNotifications();
}

watch(
    () => config.value.enable_notification_system,
    () => {
        if (config.value.enable_notification_system) {
            getNotificationsPreferences();
        }
    },
    { immediate: true }
);

function onCategoryEnabledChange(category: NotificationCategory, value: boolean) {
    notificationsPreferences.value[category]!.enabled = value;
}

function onChannelChange(category: NotificationCategory, channel: NotificationChannel, value: boolean) {
    notificationsPreferences.value[category]!.channels[channel] = value;
}
</script>

<template>
    <section class="notifications-preferences">
        <Heading
            h1
            :separator="props.embedded"
            inline
            size="xl"
            class="notifications-preferences-header"
            :class="headerSize">
            管理通知首选项
        </Heading>

        <div v-if="config.enable_notification_system" v-localize class="notifications-preferences-description">
            您可以在此处管理通知渠道和首选项。
        </div>

        <div v-else v-localize class="notifications-preferences-description">
            您可以在此处管理推送通知首选项。
        </div>

        <BAlert v-if="errorMessage" show dismissible fade variant="warning" @dismissed="errorMessage = null">
            {{ errorMessage }}
        </BAlert>

        <BAlert v-if="loading" class="m-2" show variant="info">
            <LoadingSpan message="正在加载通知首选项" />
        </BAlert>

        <div v-else-if="showPreferences" class="notifications-preferences-body">
            <div v-for="category in categories" :key="category" class="card-container">
                <NotificationsCategorySettings
                    :preferences="notificationsPreferences"
                    :supported-channels="supportedChannels"
                    :category="category"
                    @onCategoryEnabledChange="onCategoryEnabledChange"
                    @onChannelChange="onChannelChange" />
            </div>
        </div>

        <div
            v-if="!loading && browserSupportsPushNotifications() && !pushNotificationsGranted"
            class="card-container push-notifications-notice">
            允许推送和标签通知。若要禁用，请在浏览器中撤销站点通知权限。
            <BButton
                v-b-tooltip.hover
                class="mx-2"
                title="启用推送通知"
                @click="onTogglePushNotifications">
                启用推送通知
            </BButton>
        </div>

        <BAlert
            v-else-if="!loading && browserSupportsPushNotifications() && pushNotificationsGranted"
            show
            variant="info"
            class="my-2">
            <FontAwesomeIcon :icon="faCheckCircle" />
            推送通知已启用。您可以通过在浏览器中撤销站点通知权限来禁用它们。
        </BAlert>

        <BAlert v-else-if="!loading" show variant="warning" class="my-2">
            <FontAwesomeIcon :icon="faExclamationCircle" />
            此浏览器不支持推送通知。您仍然可以接收应用内通知。
        </BAlert>

        <div v-if="!loading && config.enable_notification_system" class="d-flex justify-content-center">
            <AsyncButton :action="updateNotificationsPreferences" :icon="faSave" variant="primary" size="md">
                <span v-localize>保存</span>
            </AsyncButton>
        </div>
    </section>
</template>

<style scoped lang="scss">
.notifications-preferences {
    .notifications-preferences-header {
        flex-grow: 1;
    }

    .notifications-preferences-description {
        margin-bottom: 1rem;
    }

    .notifications-preferences-body {
        display: flex;
        justify-content: space-around;
    }

    .push-notifications-notice {
        margin: 0.5rem auto;
        width: fit-content;
    }
}

.card-container {
    margin: 0.5rem;
}
</style>

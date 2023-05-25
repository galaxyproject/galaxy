<script setup lang="ts">
import Vue, { computed, ref } from "vue";
import BootstrapVue from "bootstrap-vue";
import type { components } from "@/schema";
import { Toast } from "@/composables/toast";
import { useConfig } from "@/composables/config";
import LoadingSpan from "@/components/LoadingSpan.vue";
import { library } from "@fortawesome/fontawesome-svg-core";
import AsyncButton from "@/components/Common/AsyncButton.vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faExclamationCircle } from "@fortawesome/free-solid-svg-icons";
import {
    browserSupportsPushNotifications,
    pushNotificationsEnabled,
    togglePushNotifications,
} from "@/composables/utils/pushNotifications";
import {
    getNotificationsPreferencesFromServer,
    updateNotificationsPreferencesOnServer,
} from "@/components/User/Notifications/model/services";

Vue.use(BootstrapVue);

library.add(faExclamationCircle);

defineProps({
    headerSize: {
        type: String,
        default: "h-lg",
    },
});

type UserNotificationPreferences = components["schemas"]["UserNotificationPreferences"];

const { config } = useConfig();

const loading = ref(false);
const errorMessage = ref<string | null>(null);
const pushNotificationsGranted = ref(pushNotificationsEnabled());
const categories = computed(() => Object.keys(notificationsPreferences.value));
const notificationsPreferences = ref<UserNotificationPreferences["preferences"]>({});

async function getNotificationsPreferences() {
    loading.value = true;
    await getNotificationsPreferencesFromServer()
        .then((data) => {
            notificationsPreferences.value = data.preferences;
        })
        .catch((error: any) => {
            errorMessage.value = error;
        })
        .finally(() => {
            loading.value = false;
        });
}

async function updateNotificationsPreferences() {
    await updateNotificationsPreferencesOnServer({ preferences: notificationsPreferences.value })
        .then((data) => {
            notificationsPreferences.value = data.preferences;
            Toast.success("Notifications preferences updated");
        })
        .catch((error: any) => {
            errorMessage.value = error;
        });
}

function capitalizeWords(str: string): string {
    return str
        .split("_")
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(" ");
}

async function onTogglePushNotifications() {
    pushNotificationsGranted.value = await togglePushNotifications();
}

if (config.value.enable_notification_system) {
    getNotificationsPreferences();
}
</script>

<template>
    <section class="notifications-preferences">
        <h1 v-localize :class="headerSize">Manage notifications preferences</h1>

        <span v-if="config.enable_notification_system" v-localize class="mb-2">
            You can manage notifications channels and preferences here.
        </span>
        <span v-else v-localize class="mb-2"> You can manage push notifications preferences here. </span>

        <BAlert v-if="errorMessage" show dismissible fade variant="warning" @dismissed="errorMessage = null">
            {{ errorMessage }}
        </BAlert>

        <BAlert v-if="loading" class="m-2" show variant="info">
            <LoadingSpan message="Loading notifications preferences" />
        </BAlert>

        <BRow v-else-if="!loading && config.enable_notification_system && notificationsPreferences" class="mx-1">
            <BCol v-for="category in categories" :key="category">
                <BCard class="my-2">
                    <BRow align-h="between" align-v="center">
                        <BCol cols="auto">
                            <span v-localize>{{ capitalizeWords(category) }}</span>
                        </BCol>
                        <BCol cols="auto">
                            <BCheckbox
                                v-model="notificationsPreferences[category].enabled"
                                v-b-tooltip.hover
                                :title="
                                    notificationsPreferences[category].enabled
                                        ? 'Disable notifications'
                                        : 'Enable notifications'
                                "
                                switch />
                        </BCol>
                    </BRow>
                    <BCollapse v-model="notificationsPreferences[category].enabled">
                        <BRow class="p-2">
                            <BCol
                                v-for="channel in Object.keys(notificationsPreferences[category].channels)"
                                :key="channel"
                                class="d-flex align-items-center">
                                <BFormCheckbox
                                    v-model="notificationsPreferences[category].channels[channel]"
                                    v-localize>
                                    {{ capitalizeWords(channel) }}
                                </BFormCheckbox>
                                <BButton
                                    v-if="channel === 'push'"
                                    v-b-tooltip.hover
                                    variant="link"
                                    class="mx-2"
                                    title="Push notifications need to be enabled">
                                    <FontAwesomeIcon icon="exclamation-circle" />
                                </BButton>
                            </BCol>
                        </BRow>
                    </BCollapse>
                </BCard>
            </BCol>
        </BRow>

        <BRow v-if="!loading" class="m-1" align-h="center">
            <BCard v-if="browserSupportsPushNotifications() && !pushNotificationsGranted" class="my-2">
                Allow push and tab notifications. To disable, revoke the site notification privilege in your browser.
                <BButton
                    v-b-tooltip.hover
                    class="mx-2"
                    title="Enable push notifications"
                    @click="onTogglePushNotifications">
                    Enable push notifications
                </BButton>
            </BCard>
            <BAlert
                v-else-if="browserSupportsPushNotifications() && pushNotificationsGranted"
                show
                variant="info"
                class="my-2">
                <FontAwesomeIcon icon="check-circle" />
                Push notifications are enabled. You can disable them by revoking the site notification privilege in your
                browser.
            </BAlert>
            <BAlert v-else show variant="warning" class="my-2">
                <FontAwesomeIcon icon="exclamation-circle" />
                Push notifications are not supported by this browser. You can still receive in-app notifications.
            </BAlert>
        </BRow>

        <BRow v-if="!loading && config.enable_notification_system" class="m-1" align-h="center">
            <AsyncButton :action="updateNotificationsPreferences" icon="save" variant="primary" size="md">
                <span v-localize>Save</span>
            </AsyncButton>
        </BRow>
    </section>
</template>

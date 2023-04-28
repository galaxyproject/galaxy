<script setup lang="ts">
import Vue, { computed, ref } from "vue";
import BootstrapVue from "bootstrap-vue";
import type { components } from "@/schema";
import { Toast } from "@/composables/toast";
import LoadingSpan from "@/components/LoadingSpan.vue";
import { library } from "@fortawesome/fontawesome-svg-core";
import AsyncButton from "@/components/Common/AsyncButton.vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faExclamationCircle } from "@fortawesome/free-solid-svg-icons";
import {
    getNotificationsPreferencesFromServer,
    updateNotificationsPreferencesOnServer,
} from "@/components/User/Notifications/model/services";

Vue.use(BootstrapVue);

// @ts-ignore
library.add(faExclamationCircle);

type UserNotificationPreferences = components["schemas"]["UserNotificationPreferences"];

const loading = ref(false);
const errorMessage = ref(null);
const notificationsPreferences = ref<UserNotificationPreferences["preferences"]>({});
const categories = computed(() => Object.keys(notificationsPreferences.value));
const pushNotificationsGranted = computed(() => {
    return window.Notification && Notification.permission === "granted";
});

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

function togglePushNotifications() {
    if (window.Notification) {
        Notification.requestPermission().then(function (permission) {
            if (permission === "granted") {
                new Notification("Notifications enabled", {
                    icon: "static/favicon.ico",
                });
            } else {
                alert("Notifications disabled, please re-enable through browser settings.");
            }
        });
    } else {
        alert("Notifications are not supported by this browser.");
    }
}

getNotificationsPreferences();
</script>

<template>
    <section class="notifications-preferences">
        <h1 v-localize class="h-lg">Manage notifications preferences</h1>

        <span v-localize class="mb-2"> You can manage notifications channels and preferences here. </span>

        <BAlert v-if="errorMessage" show dismissible fade variant="warning" @dismissed="errorMessage = null">
            {{ errorMessage }}
        </BAlert>

        <BAlert v-if="loading" class="m-2" show variant="info">
            <LoadingSpan message="Loading notifications preferences" />
        </BAlert>

        <BRow v-else-if="!loading && notificationsPreferences" class="mx-1">
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
                                class="d-flex align-items-center"
                                v-for="channel in Object.keys(notificationsPreferences[category].channels)"
                                :key="channel">
                                <BFormCheckbox
                                    v-model="notificationsPreferences[category].channels[channel]"
                                    v-localize>
                                    {{ capitalizeWords(channel) }}
                                </BFormCheckbox>
                                <BButton
                                    v-if="channel === 'push'"
                                    variant="link"
                                    class="mx-2"
                                    v-b-tooltip.hover
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
            <BCard class="my-2">
                Allow push and tab notifications. To disable, revoke the site notification privilege in your browser.
                <BButton
                    class="mx-2"
                    @click="togglePushNotifications"
                    :disabled="pushNotificationsGranted"
                    v-b-tooltip.hover
                    :title="
                        pushNotificationsGranted ? 'Push notifications enabled' : 'Click to enable push notifications'
                    ">
                    Enable push notifications
                </BButton>
            </BCard>
        </BRow>

        <BRow v-if="!loading" class="m-1" align-h="center">
            <AsyncButton :action="updateNotificationsPreferences" icon="save" variant="primary" size="md">
                <span v-localize>Save</span>
            </AsyncButton>
        </BRow>
    </section>
</template>

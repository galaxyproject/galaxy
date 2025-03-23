<script setup lang="ts">
import { faInbox, faInfoCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BCol, BFormGroup, BRow } from "bootstrap-vue";
import { computed, type Ref, ref } from "vue";
import { useRouter } from "vue-router/composables";

import { GalaxyApi } from "@/api";
import { type MessageNotificationCreateRequest } from "@/api/notifications";
import { useMarkdown } from "@/composables/markdown";
import { Toast } from "@/composables/toast";
import { errorMessageAsString } from "@/utils/simple-error";

import AsyncButton from "@/components/Common/AsyncButton.vue";
import GCard from "@/components/Common/GCard.vue";
import Heading from "@/components/Common/Heading.vue";
import FormElement from "@/components/Form/FormElement.vue";
import GDateTime from "@/components/GDateTime.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

type SelectOption = [string, string];

const router = useRouter();

const { renderMarkdown } = useMarkdown({ openLinksInNewPage: true });

const loading = ref(false);
const roles = ref<SelectOption[]>([]);
const users = ref<SelectOption[]>([]);
const groups = ref<SelectOption[]>([]);
const notificationData = ref<MessageNotificationCreateRequest>({
    notification: {
        source: "admin",
        category: "message",
        variant: "info",
        content: {
            category: "message",
            subject: "",
            message: "",
        },
        expiration_time: new Date(Date.now() + 6 * 30 * 24 * 60 * 60 * 1000).toISOString().slice(0, 16),
        publication_time: new Date().toISOString().slice(0, 16),
    },
    recipients: {
        user_ids: [],
        role_ids: [],
        group_ids: [],
    },
});

const requiredFieldsFilled = computed(() => {
    return (
        notificationData.value.notification.content.subject !== "" &&
        notificationData.value.notification.content.message !== "" &&
        (notificationData.value.recipients.user_ids?.length ||
            notificationData.value.recipients.role_ids?.length ||
            notificationData.value.recipients.group_ids?.length)
    );
});

const publicationDate = computed({
    get: () => {
        return new Date(`${notificationData.value.notification.publication_time}Z`);
    },
    set: (value: Date) => {
        notificationData.value.notification.publication_time = value.toISOString().slice(0, 16);
    },
});

const expirationDate = computed({
    get: () => {
        return new Date(`${notificationData.value.notification.expiration_time}Z`);
    },
    set: (value: Date) => {
        notificationData.value.notification.expiration_time = value.toISOString().slice(0, 16);
    },
});

const isUrgent = computed(() => notificationData.value.notification.variant === "urgent");

async function loadData<T>(
    getData: () => Promise<T[]>,
    target: Ref<SelectOption[]>,
    formatter: (item: T) => SelectOption
) {
    const tmp = await getData();
    target.value = tmp.map(formatter);
}

async function getAllGroups() {
    const { data, error } = await GalaxyApi().GET("/api/groups");
    if (error) {
        Toast.error(errorMessageAsString(error));
        return [];
    }
    return data;
}

async function getAllRoles() {
    const { data, error } = await GalaxyApi().GET("/api/roles");
    if (error) {
        Toast.error(errorMessageAsString(error));
        return [];
    }
    return data;
}

// TODO: this can potentially be a very large list, consider adding filters
async function getAllUsers() {
    const { data, error } = await GalaxyApi().GET("/api/users");
    if (error) {
        Toast.error(errorMessageAsString(error));
        return [];
    }
    return data;
}

loadData(getAllUsers, users, (user) => {
    return [`${user.username} | ${user.email}`, user.id];
});

loadData(getAllRoles, roles, (role) => {
    return [`${role.name} | ${role.description}`, role.id];
});

loadData(getAllGroups, groups, (group) => {
    return [`${group.name}`, group.id];
});

async function sendNewNotification() {
    const { error } = await GalaxyApi().POST("/api/notifications", {
        body: notificationData.value,
    });

    if (error) {
        Toast.error(errorMessageAsString(error));
        return;
    }

    Toast.success("Notification sent");
    router.push("/admin/notifications");
}
</script>

<template>
    <div>
        <Heading h1 separator inline class="flex-grow-1"> New Notification </Heading>

        <BAlert v-if="loading" show>
            <LoadingSpan message="Loading notification" />
        </BAlert>

        <div v-else>
            <FormElement
                id="notification-subject"
                v-model="notificationData.notification.content.subject"
                type="text"
                title="Subject"
                :optional="false"
                help="This will be the subject of the notification"
                placeholder="Enter subject"
                required />

            <FormElement
                id="notification-message"
                v-model="notificationData.notification.content.message"
                type="text"
                title="Message"
                :optional="false"
                help="The message can be written in markdown."
                placeholder="Enter message"
                required
                area />

            <FormElement
                id="notification-variant"
                v-model="notificationData.notification.variant"
                type="select"
                title="Variant"
                :optional="false"
                help="This measures the urgency of the notification and will affect the color of the notification."
                :options="[
                    ['Info', 'info'],
                    ['Warning', 'warning'],
                    ['Urgent', 'urgent'],
                ]" />

            <BAlert :show="isUrgent" variant="warning">
                <span v-localize>
                    Urgent notifications will ignore the user's notification preferences and will be sent to all
                    available channels. Please use this option sparingly and only for critical notifications.
                </span>
            </BAlert>

            <FormElement
                id="notification-recipients-user-ids"
                v-model="notificationData.recipients.user_ids"
                type="select"
                title="User recipients"
                help="The users that will receive the notification"
                multiple
                :options="users" />

            <FormElement
                id="notification-recipients-role-ids"
                v-model="notificationData.recipients.role_ids"
                type="select"
                title="Role recipients"
                help="The roles that will receive the notification"
                multiple
                :options="roles" />

            <FormElement
                id="notification-recipients-group-ids"
                v-model="notificationData.recipients.group_ids"
                type="select"
                title="Group recipients"
                help="The groups that will receive the notification"
                multiple
                :options="groups" />

            <BRow align-v="center">
                <BCol>
                    <BFormGroup
                        id="notification-publication-time-group"
                        label="Publication Time (local time)"
                        label-for="notification-publication-time"
                        description="The notification will be displayed after this time. Default is the current time.">
                        <GDateTime id="notification-publication-time" v-model="publicationDate" />
                    </BFormGroup>
                </BCol>
                <BCol>
                    <BFormGroup
                        id="notification-expiration-time-group"
                        label="Expiration Time (local time)"
                        label-for="notification-expiration-time"
                        description="The notification will be deleted from the database after this time. Default is 6 months from the creation time.">
                        <GDateTime id="notification-expiration-time" v-model="expirationDate" />
                    </BFormGroup>
                </BCol>
            </BRow>

            <BRow align-v="center" class="m-1">
                <Heading size="md"> Preview </Heading>
            </BRow>

            <GCard
                id="notification-preview"
                :title="notificationData.notification.content.subject"
                :title-icon="{
                    icon: faInbox,
                    class: `text-${isUrgent ? 'danger' : notificationData.notification.variant}`,
                }"
                :description="notificationData.notification.content.message"
                :update-time-title="`Published ${notificationData.notification.publication_time ? 'on' : 'at'}`"
                @tagClick="() => {}">
                <template v-slot:description>
                    <span
                        id="notification-message"
                        class="notification-message"
                        v-html="renderMarkdown(notificationData.notification.content.message)" />
                </template>
            </GCard>

            <BAlert show variant="info">
                <FontAwesomeIcon class="mr-2" :icon="faInfoCircle" />
                <span v-localize>
                    Once you send the notification, it will be sent to all the recipients and cannot be edited or
                    deleted.
                </span>
            </BAlert>

            <BRow class="m-2" align-h="center">
                <AsyncButton
                    id="notification-submit"
                    icon="save"
                    :title="!requiredFieldsFilled ? 'Please fill all required fields' : ''"
                    variant="primary"
                    size="md"
                    :disabled="!requiredFieldsFilled"
                    :action="sendNewNotification">
                    <span v-localize> Send Notification </span>
                </AsyncButton>
            </BRow>
        </div>
    </div>
</template>

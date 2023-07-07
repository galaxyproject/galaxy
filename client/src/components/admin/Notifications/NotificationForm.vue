<script setup lang="ts">
import { BAlert, BCard, BCol, BFormGroup, BFormInput, BRow } from "bootstrap-vue";
import { format } from "date-fns";
import { computed, type Ref, ref } from "vue";
import { useRouter } from "vue-router/composables";

import {
    getGroups,
    getRoles,
    getUsers,
    sendNotification,
} from "@/components/admin/Notifications/notifications.services";
import { Toast } from "@/composables/toast";
import { type components } from "@/schema";

import AsyncButton from "@/components/Common/AsyncButton.vue";
import Heading from "@/components/Common/Heading.vue";
import FormElement from "@/components/Form/FormElement.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import MessageNotification from "@/components/Notifications/Categories/MessageNotification.vue";

const dateTimeFormat = "yyyy-MM-dd'T'HH:mm:ss.SSSSSS";

type SelectOption = [string, string];
type NotificationCreateData = components["schemas"]["NotificationCreateData"];
type NotificationCreateRequest = components["schemas"]["NotificationCreateRequest"];

interface MessageNotificationCreateData extends NotificationCreateData {
    category: "message";
    content: components["schemas"]["MessageNotificationContent"];
}

interface MessageNotificationCreateRequest extends NotificationCreateRequest {
    notification: MessageNotificationCreateData;
}

const router = useRouter();

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

async function loadData<T>(
    getData: () => Promise<T[]>,
    target: Ref<SelectOption[]>,
    formatter: (item: T) => SelectOption
) {
    try {
        const tmp = await getData();
        target.value = tmp.map(formatter);
    } catch (error: any) {
        Toast.error(error.err_msg);
    }
}

loadData(getUsers, users, (user) => {
    return [`${user.username} | ${user.email}`, user.id];
});

loadData(getRoles, roles, (role) => {
    return [`${role.name} | ${role.description}`, role.id];
});

loadData(getGroups, groups, (group) => {
    return [`${group.name}`, group.id];
});

async function sendNewNotification() {
    try {
        const tmp = notificationData.value;

        if (tmp.notification.publication_time) {
            tmp.notification.publication_time = format(new Date(tmp.notification.publication_time), dateTimeFormat);
        }

        if (tmp.notification.expiration_time) {
            tmp.notification.expiration_time = format(new Date(tmp.notification.expiration_time), dateTimeFormat);
        }

        await sendNotification(tmp);
        Toast.success("Notification sent");
        router.push("/admin/notifications");
    } catch (error: any) {
        Toast.error(error.err_msg);
    }
}
</script>

<template>
    <div>
        <Heading> New Notification </Heading>

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
                required />

            <FormElement
                id="notification-variant"
                v-model="notificationData.notification.variant"
                type="select"
                title="Variant"
                :optional="false"
                help="This will change the color of the notification"
                :options="[
                    ['Info', 'info'],
                    ['Warning', 'warning'],
                    ['Urgent', 'urgent'],
                ]" />

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
                        label="Publication Time"
                        label-for="notification-publication-time"
                        description="The notification will be displayed after this time. Default is the current time.">
                        <BFormInput
                            id="notification-publication-time"
                            v-model="notificationData.notification.publication_time"
                            type="datetime-local"
                            placeholder="Enter publication time"
                            required />
                    </BFormGroup>
                </BCol>
                <BCol>
                    <BFormGroup
                        id="notification-expiration-time-group"
                        label="Expiration Time"
                        label-for="notification-expiration-time"
                        description="The notification will be deleted from the database after this time. Default is 6 months from the creation time.">
                        <BFormInput
                            id="notification-expiration-time"
                            v-model="notificationData.notification.expiration_time"
                            type="datetime-local"
                            placeholder="Enter expiration time"
                            required />
                    </BFormGroup>
                </BCol>
            </BRow>

            <BRow class="m-2" align-h="center">
                <AsyncButton
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

<script setup lang="ts">
import { computed, ref } from "vue";
import { type components } from "@/schema";
import { Toast } from "@/composables/toast";
import { useRouter } from "vue-router/composables";
import Heading from "@/components/Common/Heading.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import FormElement from "@/components/Form/FormElement.vue";
import AsyncButton from "@/components/Common/AsyncButton.vue";
import {
    createNotification,
    getGroups,
    getRoles,
    getUsers,
} from "@/components/admin/Notifications/notifications.services";

type NotificationRecipients = components["schemas"]["NotificationRecipients"];

type NotificationCreateData = {
    source: string;
    category: "message";
    variant: "info" | "warning" | "urgent";
    content: {
        category: "message";
        subject: string;
        message: string;
    };
};

const props = defineProps({
    id: {
        type: String,
        default: null,
    },
});

const router = useRouter();

const loading = ref(false);
const roles = ref<[string, string][]>([]);
const users = ref<[string, string][]>([]);
const groups = ref<[string, string][]>([]);
const recipients = ref<NotificationRecipients>({
    role_ids: [],
    user_ids: [],
    group_ids: [],
});
const notification = ref<NotificationCreateData>({
    source: "admin",
    category: "message",
    variant: "info",
    content: {
        category: "message",
        subject: "",
        message: "",
    },
});

const title = computed(() => {
    if (props.id) {
        return "Edit Notification";
    } else {
        return "New Notification";
    }
});
const requiredFieldsFilled = computed(() => {
    return (
        notification.value.content.subject !== "" ||
        notification.value.content.message !== "" ||
        (recipients.value.user_ids?.length !== 0 &&
            recipients.value.role_ids?.length !== 0 &&
            recipients.value.group_ids?.length !== 0)
    );
});

async function loadUsers() {
    try {
        const tmp = await getUsers();
        users.value = tmp.map((user) => {
            return [`${user.username} | ${user.email}`, user.id];
        });
    } catch (error: any) {
        Toast.error(error.err_msg);
    }
}

async function loadRoles() {
    try {
        const tmp = await getRoles();
        roles.value = tmp.map((role) => {
            return [`${role.name} | ${role.description}`, role.id];
        });
    } catch (error: any) {
        Toast.error(error.err_msg);
    }
}

async function loadGroups() {
    try {
        const tmp = await getGroups();
        groups.value = tmp.map((group) => {
            return [`${group.name}`, group.id];
        });
    } catch (error: any) {
        Toast.error(error.err_msg);
    }
}

loadUsers();
loadRoles();
loadGroups();

async function createNewNotification() {
    try {
        await createNotification({
            recipients: recipients.value,
            notification: notification.value,
        });
        Toast.success("Notification created");
        router.push("/admin/notifications");
    } catch (error: any) {
        Toast.error(error.err_msg);
    }
}
</script>

<template>
    <div>
        <Heading> {{ title }} </Heading>

        <BAlert v-if="loading" show>
            <LoadingSpan message="Loading notification" />
        </BAlert>

        <div v-else>
            <FormElement
                id="notification-subject"
                v-model="notification.content.subject"
                type="text"
                title="Subject"
                :optional="false"
                help="This will be the subject of the notification"
                placeholder="Enter subject"
                required />

            <FormElement
                id="notification-message"
                v-model="notification.content.message"
                type="text"
                title="Message"
                :optional="false"
                help="The message can be written in markdown."
                placeholder="Enter message"
                required />

            <FormElement
                id="notification-variant"
                v-model="notification.variant"
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
                v-model="recipients.user_ids"
                type="select"
                title="User recipients"
                help="The users that will receive the notification"
                multiple
                :options="users" />

            <FormElement
                id="notification-recipients-role-ids"
                v-model="recipients.role_ids"
                type="select"
                title="Role recipients"
                help="The roles that will receive the notification"
                multiple
                :options="roles" />

            <FormElement
                id="notification-recipients-group-ids"
                v-model="recipients.group_ids"
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
                            :value.sync="notification.publication_time"
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
                            v-model="notification.expiration_time"
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
                    :action="createNewNotification">
                    <span v-if="props.id" v-localize> Update Notification </span>
                    <span v-else v-localize> Create Notification </span>
                </AsyncButton>
            </BRow>
        </div>
    </div>
</template>

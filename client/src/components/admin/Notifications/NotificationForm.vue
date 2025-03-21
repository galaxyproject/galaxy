<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faInfoCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BCard, BCol, BFormGroup, BRow } from "bootstrap-vue";
import { computed, type Ref, ref } from "vue";
import { useRouter } from "vue-router/composables";

import { GalaxyApi } from "@/api";
import { type MessageNotificationCreateRequest } from "@/api/notifications";
import { Toast } from "@/composables/toast";
import { errorMessageAsString } from "@/utils/simple-error";

import AsyncButton from "@/components/Common/AsyncButton.vue";
import Heading from "@/components/Common/Heading.vue";
import FormElement from "@/components/Form/FormElement.vue";
import GDateTime from "@/components/GDateTime.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import MessageNotification from "@/components/Notifications/Categories/MessageNotification.vue";

library.add(faInfoCircle);

type SelectOption = [string, string];

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

    Toast.success("通知已发送");
    router.push("/admin/notifications");
}
</script>

<template>
    <div>
        <Heading h1 separator inline class="flex-grow-1"> 新通知 </Heading>

        <BAlert v-if="loading" show>
            <LoadingSpan message="加载通知" />
        </BAlert>

        <div v-else>
            <FormElement
                id="notification-subject"
                v-model="notificationData.notification.content.subject"
                type="text"
                title="主题"
                :optional="false"
                help="这将是通知的主题"
                placeholder="请输入主题"
                required />

            <FormElement
                id="notification-message"
                v-model="notificationData.notification.content.message"
                type="text"
                title="消息"
                :optional="false"
                help="消息可以使用 markdown 格式编写。"
                placeholder="请输入消息"
                required
                area />

            <FormElement
                id="notification-variant"
                v-model="notificationData.notification.variant"
                type="select"
                title="变体"
                :optional="false"
                help="此选项衡量通知的紧急性，并将影响通知的颜色。"
                :options="[ 
                    ['信息', 'info'],
                    ['警告', 'warning'],
                    ['紧急', 'urgent'],
                ]" />

            <BAlert :show="isUrgent" variant="warning">
                <span v-localize>
                    紧急通知将忽略用户的通知偏好，并会发送到所有可用的频道。请谨慎使用此选项，仅用于关键通知。
                </span>
            </BAlert>

            <FormElement
                id="notification-recipients-user-ids"
                v-model="notificationData.recipients.user_ids"
                type="select"
                title="用户接收者"
                help="将接收通知的用户"
                multiple
                :options="users" />

            <FormElement
                id="notification-recipients-role-ids"
                v-model="notificationData.recipients.role_ids"
                type="select"
                title="角色接收者"
                help="将接收通知的角色"
                multiple
                :options="roles" />

            <FormElement
                id="notification-recipients-group-ids"
                v-model="notificationData.recipients.group_ids"
                type="select"
                title="组接收者"
                help="将接收通知的组"
                multiple
                :options="groups" />

            <BRow align-v="center">
                <BCol>
                    <BFormGroup
                        id="notification-publication-time-group"
                        label="发布时间（本地时间）"
                        label-for="notification-publication-time"
                        description="通知将在此时间之后显示。默认为当前时间。">
                        <GDateTime id="notification-publication-time" v-model="publicationDate" />
                    </BFormGroup>
                </BCol>
                <BCol>
                    <BFormGroup
                        id="notification-expiration-time-group"
                        label="过期时间（本地时间）"
                        label-for="notification-expiration-time"
                        description="通知将在此时间之后从数据库中删除。默认为创建时间后的6个月。">
                        <GDateTime id="notification-expiration-time" v-model="expirationDate" />
                    </BFormGroup>
                </BCol>
            </BRow>

            <BRow align-v="center" class="m-1">
                <Heading size="md"> 预览 </Heading>
            </BRow>

            <BCard class="my-2">
                <MessageNotification :options="{ notification: notificationData.notification, previewMode: true }" />
            </BCard>

            <BAlert show variant="info">
                <FontAwesomeIcon class="mr-2" :icon="faInfoCircle" />
                <span v-localize>
                    一旦发送通知，它将发送给所有接收者，并且无法编辑或删除。
                </span>
            </BAlert>

            <BRow class="m-2" align-h="center">
                <AsyncButton
                    id="notification-submit"
                    icon="save"
                    :title="!requiredFieldsFilled ? '请填写所有必填字段' : ''"
                    variant="primary"
                    size="md"
                    :disabled="!requiredFieldsFilled"
                    :action="sendNewNotification">
                    <span v-localize> 发送通知 </span>
                </AsyncButton>
            </BRow>
        </div>
    </div>
</template>
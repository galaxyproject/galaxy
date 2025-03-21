<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton, BCol, BFormGroup, BFormInput, BRow } from "bootstrap-vue";
import Vue, { computed, ref } from "vue";
import { useRouter } from "vue-router/composables";

import { type components, GalaxyApi } from "@/api";
import { createBroadcast, updateBroadcast } from "@/api/notifications.broadcast";
import { Toast } from "@/composables/toast";
import { errorMessageAsString } from "@/utils/simple-error";

import AsyncButton from "@/components/Common/AsyncButton.vue";
import Heading from "@/components/Common/Heading.vue";
import FormElement from "@/components/Form/FormElement.vue";
import GDateTime from "@/components/GDateTime.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import BroadcastContainer from "@/components/Notifications/Broadcasts/BroadcastContainer.vue";

type BroadcastNotificationCreateRequest = components["schemas"]["BroadcastNotificationCreateRequest"];

const props = defineProps({
    id: {
        type: String,
        default: null,
    },
});

const router = useRouter();

const title = computed(() => {
    if (props.id) {
        return "编辑广播";
    } else {
        return "新建广播";
    }
});

const loading = ref(false);

const broadcastData = ref<BroadcastNotificationCreateRequest>({
    source: "admin",
    variant: "info",
    category: "broadcast",
    content: {
        category: "broadcast",
        subject: "",
        message: "",
    },
    expiration_time: new Date(Date.now() + 6 * 30 * 24 * 60 * 60 * 1000).toISOString().slice(0, 16),
    publication_time: new Date().toISOString().slice(0, 16),
});

const broadcastPublished = ref(false);
const requiredFieldsFilled = computed(() => {
    return broadcastData.value.content.subject !== "" && broadcastData.value.content.message !== "";
});

const publicationDate = computed({
    get: () => {
        return new Date(`${broadcastData.value.publication_time}Z`);
    },
    set: (value: Date) => {
        broadcastData.value.publication_time = value.toISOString().slice(0, 16);
    },
});

const expirationDate = computed({
    get: () => {
        return new Date(`${broadcastData.value.expiration_time}Z`);
    },
    set: (value: Date) => {
        broadcastData.value.expiration_time = value.toISOString().slice(0, 16);
    },
});

function convertUTCtoLocal(utcTimeString: string) {
    const date = new Date(utcTimeString);
    return new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
}

function addActionLink() {
    if (!broadcastData.value.content.action_links) {
        Vue.set(broadcastData.value.content, "action_links", []);
    }

    broadcastData.value.content.action_links?.push({
        action_name: "",
        link: "",
    });
}

async function createOrUpdateBroadcast() {
    try {
        if (props.id) {
            await updateBroadcast(props.id, broadcastData.value);
            Toast.success("广播已更新");
        } else {
            await createBroadcast(broadcastData.value);
            Toast.success("广播已创建");
        }
    } catch (error: any) {
        Toast.error(errorMessageAsString(error));
    } finally {
        router.push("/admin/notifications");
    }
}

async function loadBroadcastData() {
    loading.value = true;
    try {
        const { data: loadedBroadcast, error } = await GalaxyApi().GET(
            "/api/notifications/broadcast/{notification_id}",
            {
                params: {
                    path: { notification_id: props.id },
                },
            }
        );

        if (error) {
            Toast.error(errorMessageAsString(error));
            return;
        }

        broadcastData.value.publication_time = convertUTCtoLocal(loadedBroadcast.publication_time);

        if (loadedBroadcast.expiration_time) {
            broadcastData.value.expiration_time = convertUTCtoLocal(loadedBroadcast.expiration_time);
        }

        broadcastData.value = loadedBroadcast;

        if (broadcastData.value.publication_time) {
            broadcastPublished.value = new Date(broadcastData.value.publication_time) < new Date();
        }
    } finally {
        loading.value = false;
    }
}

if (props.id) {
    loadBroadcastData();
}
</script>

<template>
    <div>
        <Heading h1 separator inline class="flex-grow-1"> {{ title }} </Heading>

        <BAlert v-if="loading" show>
            <LoadingSpan message="加载广播" />
        </BAlert>

        <div v-else>
            <BAlert v-if="props.id && broadcastPublished" id="broadcast-published-warning" variant="warning" show>
                该广播已经发布。一些用户可能已经看到了它，修改此广播将不会影响这些用户。
            </BAlert>

            <FormElement
                id="broadcast-subject"
                v-model="broadcastData.content.subject"
                type="text"
                title="主题"
                :optional="false"
                help="此内容将显示在广播横幅中，应该简短明确。"
                placeholder="请输入主题"
                required />

            <FormElement
                id="broadcast-variant"
                v-model="broadcastData.variant"
                type="select"
                title="变体"
                :optional="false"
                help="此设置将决定广播横幅的位置和图标。紧急广播会显示在页面顶部，否则会显示在底部。"
                :options="[ 
                    ['信息', 'info'],
                    ['警告', 'warning'],
                    ['紧急', 'urgent']
                ]" />

            <FormElement
                id="broadcast-message"
                v-model="broadcastData.content.message"
                type="text"
                title="消息"
                :optional="false"
                help="消息内容可以使用 markdown 格式。"
                placeholder="请输入消息"
                required
                area />

            <BFormGroup id="broadcast-action-link-group" label="操作链接" label-for="broadcast-action-link">
                <BRow v-for="(actionLink, index) in broadcastData.content.action_links" :key="index" class="my-2">
                    <BCol cols="auto">
                        <BFormInput
                            :id="`broadcast-action-link-name-${index}`"
                            v-model="actionLink.action_name"
                            type="text"
                            placeholder="请输入操作名称"
                            required />
                    </BCol>
                    <BCol>
                        <BFormInput
                            :id="`broadcast-action-link-link-${index}`"
                            v-model="actionLink.link"
                            type="url"
                            placeholder="请输入操作链接"
                            required />
                    </BCol>
                    <BCol cols="auto">
                        <BButton
                            :id="`delete-action-link-${index}}`"
                            v-b-tooltip.hover.bottom
                            title="删除操作链接"
                            variant="error-outline"
                            role="button"
                            @click="
                                broadcastData.content.action_links?.splice(
                                    broadcastData.content.action_links.indexOf(actionLink),
                                    1
                                )
                            ">
                            <FontAwesomeIcon icon="times" />
                        </BButton>
                    </BCol>
                </BRow>

                <BButton
                    id="create-action-link"
                    title="添加新操作链接"
                    variant="outline-primary"
                    role="button"
                    @click="addActionLink">
                    <FontAwesomeIcon icon="plus" />
                    添加操作链接
                </BButton>
            </BFormGroup>

            <BRow>
                <BCol>
                    <BFormGroup
                        id="broadcast-publication-time-group"
                        label="发布时间（本地时间）"
                        label-for="broadcast-publication-time"
                        description="该广播将在此时间后显示。默认为创建时间。">
                        <GDateTime id="broadcast-publication-time" v-model="publicationDate" />
                    </BFormGroup>
                </BCol>
                <BCol>
                    <BFormGroup
                        id="broadcast-expiration-time-group"
                        label="过期时间（本地时间）"
                        label-for="broadcast-expiration-time"
                        description="广播将在此时间后停止显示，并从数据库中删除。默认为创建时间后的6个月。">
                        <GDateTime id="broadcast-expiration-time" v-model="expirationDate" />
                    </BFormGroup>
                </BCol>
            </BRow>

            <BRow align-v="center" class="m-1">
                <Heading size="md"> 预览 </Heading>
            </BRow>

            <BroadcastContainer :options="{ broadcast: broadcastData, previewMode: true }" />

            <BRow class="m-2" align-h="center">
                <AsyncButton
                    id="broadcast-submit"
                    icon="save"
                    :title="!requiredFieldsFilled ? '请填写所有必填字段' : ''"
                    variant="primary"
                    size="md"
                    :disabled="!requiredFieldsFilled"
                    :action="createOrUpdateBroadcast">
                    <span v-if="props.id" v-localize> 更新广播 </span>
                    <span v-else v-localize> 创建广播 </span>
                </AsyncButton>
            </BRow>
        </div>
    </div>
</template>

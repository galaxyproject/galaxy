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
        return "Edit Broadcast";
    } else {
        return "New Broadcast";
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
            Toast.success("Broadcast updated");
        } else {
            await createBroadcast(broadcastData.value);
            Toast.success("Broadcast created");
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
            <LoadingSpan message="Loading broadcast" />
        </BAlert>

        <div v-else>
            <BAlert v-if="props.id && broadcastPublished" id="broadcast-published-warning" variant="warning" show>
                This broadcast has already been published. Some users may have already seen it and changing it now will
                not affect them.
            </BAlert>

            <FormElement
                id="broadcast-subject"
                v-model="broadcastData.content.subject"
                type="text"
                title="Subject"
                :optional="false"
                help="This will be displayed in the broadcast banner. It should be short and to the point."
                placeholder="Enter subject"
                required />

            <FormElement
                id="broadcast-variant"
                v-model="broadcastData.variant"
                type="select"
                title="Variant"
                :optional="false"
                help="This will determine the position and the icon of the broadcast banner. Urgent broadcasts will be displayed at the top of the page otherwise they will be displayed at the bottom."
                :options="[
                    ['Info', 'info'],
                    ['Warning', 'warning'],
                    ['Urgent', 'urgent'],
                ]" />

            <FormElement
                id="broadcast-message"
                v-model="broadcastData.content.message"
                type="text"
                title="Message"
                :optional="false"
                help="The message can be written in markdown."
                placeholder="Enter message"
                required
                area />

            <BFormGroup id="broadcast-action-link-group" label="Action Links" label-for="broadcast-action-link">
                <BRow v-for="(actionLink, index) in broadcastData.content.action_links" :key="index" class="my-2">
                    <BCol cols="auto">
                        <BFormInput
                            :id="`broadcast-action-link-name-${index}`"
                            v-model="actionLink.action_name"
                            type="text"
                            placeholder="Enter action name"
                            required />
                    </BCol>
                    <BCol>
                        <BFormInput
                            :id="`broadcast-action-link-link-${index}`"
                            v-model="actionLink.link"
                            type="url"
                            placeholder="Enter action link"
                            required />
                    </BCol>
                    <BCol cols="auto">
                        <BButton
                            :id="`delete-action-link-${index}}`"
                            v-b-tooltip.hover.bottom
                            title="Delete action link"
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
                    title="Add new action link"
                    variant="outline-primary"
                    role="button"
                    @click="addActionLink">
                    <FontAwesomeIcon icon="plus" />
                    Add action link
                </BButton>
            </BFormGroup>

            <BRow>
                <BCol>
                    <BFormGroup
                        id="broadcast-publication-time-group"
                        label="Publication Time (local time)"
                        label-for="broadcast-publication-time"
                        description="The broadcast will be displayed from this time onwards. Default is the time of creation.">
                        <GDateTime id="broadcast-publication-time" v-model="publicationDate" />
                    </BFormGroup>
                </BCol>
                <BCol>
                    <BFormGroup
                        id="broadcast-expiration-time-group"
                        label="Expiration Time (local time)"
                        label-for="broadcast-expiration-time"
                        description="The broadcast will not be displayed and will be deleted from the database after this time. Default is 6 months from the creation time.">
                        <GDateTime id="broadcast-expiration-time" v-model="expirationDate" />
                    </BFormGroup>
                </BCol>
            </BRow>

            <BRow align-v="center" class="m-1">
                <Heading size="md"> Preview </Heading>
            </BRow>

            <BroadcastContainer :options="{ broadcast: broadcastData, previewMode: true }" />

            <BRow class="m-2" align-h="center">
                <AsyncButton
                    id="broadcast-submit"
                    icon="save"
                    :title="!requiredFieldsFilled ? 'Please fill all required fields' : ''"
                    variant="primary"
                    size="md"
                    :disabled="!requiredFieldsFilled"
                    :action="createOrUpdateBroadcast">
                    <span v-if="props.id" v-localize> Update Broadcast </span>
                    <span v-else v-localize> Create Broadcast </span>
                </AsyncButton>
            </BRow>
        </div>
    </div>
</template>

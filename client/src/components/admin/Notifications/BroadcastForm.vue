<script setup lang="ts">
import Vue, { computed, ref } from "vue";
import { type components } from "@/schema";
import { Toast } from "@/composables/toast";
import { useRouter } from "vue-router/composables";
import Heading from "@/components/Common/Heading.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import FormElement from "@/components/Form/FormElement.vue";
import AsyncButton from "@/components/Common/AsyncButton.vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import BroadcastContainer from "@/components/Notifications/Broadcasts/BroadcastContainer.vue";
import { createBroadcast, loadBroadcast, updateBroadcast } from "@/components/admin/Notifications/broadcasts.services";

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
const broadcast = ref<BroadcastNotificationCreateRequest>({
    source: "admin",
    variant: "info",
    content: {
        subject: "",
        message: "",
    },
});

const requiredFieldsFilled = computed(() => {
    return broadcast.value.content.subject !== "" && broadcast.value.content.message !== "";
});

function addActionLink() {
    if (!broadcast.value.content.action_links) {
        Vue.set(broadcast.value.content, "action_links", []);
    }

    broadcast.value.content.action_links?.push({
        action_name: "",
        link: "",
    });
}

async function createOrUpdateBroadcast() {
    try {
        if (props.id) {
            await updateBroadcast(props.id, broadcast.value);
            Toast.success("Broadcast updated");
        } else {
            await createBroadcast(broadcast.value);
            Toast.success("Broadcast created");
        }
        router.push("/admin/notifications/");
    } catch (error: any) {
        Toast.error(error.err_msg);
    }
}

async function loadBroadcastData() {
    if (props.id) {
        loading.value = true;
        try {
            broadcast.value = await loadBroadcast(props.id);
        } catch (error: any) {
            Toast.error(error.err_msg);
        }
        loading.value = false;
    }
}
loadBroadcastData();
</script>

<template>
    <div>
        <Heading> {{ title }} </Heading>

        <BAlert v-if="loading" show>
            <LoadingSpan message="Loading broadcast" />
        </BAlert>

        <div v-else>
            <FormElement
                id="broadcast-subject"
                v-model="broadcast.content.subject"
                type="text"
                title="Subject"
                :optional="false"
                help="This will be displayed in the broadcast banner. It should be short and to the point."
                placeholder="Enter subject"
                required />

            <FormElement
                id="broadcast-variant"
                v-model="broadcast.variant"
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
                v-model="broadcast.content.message"
                type="text"
                title="Message"
                :optional="false"
                help="The message can be written in markdown."
                placeholder="Enter message"
                required />

            <BFormGroup id="broadcast-action-link-group" label="Action Links" label-for="broadcast-action-link">
                <BRow
                    v-for="(actionLink, index) in broadcast.content.action_links"
                    :key="actionLink.action_name"
                    class="my-2">
                    <BCol cols="auto">
                        <BFormInput
                            :id="`broadcast-action-link-name-${{ index }}`"
                            v-model="actionLink.action_name"
                            type="text"
                            placeholder="Enter action name"
                            required />
                    </BCol>
                    <BCol>
                        <BFormInput
                            :id="`broadcast-action-link-link-${{ index }}`"
                            v-model="actionLink.link"
                            type="url"
                            placeholder="Enter action link"
                            required />
                    </BCol>
                    <BCol cols="auto">
                        <BButton
                            :id="`delete-action-link-${{ index }}}`"
                            v-b-tooltip.hover.bottom
                            title="Delete action link"
                            variant="error-outline"
                            role="button"
                            @click="
                                broadcast.content.action_links.splice(
                                    broadcast.content.action_links.indexOf(actionLink),
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

            <BRow align-v="center">
                <BCol>
                    <BFormGroup
                        id="broadcast-publication-time-group"
                        label="Publication Time"
                        label-for="broadcast-publication-time"
                        description="The broadcast will be displayed from this time onwards. Default is the time of creation.">
                        <BFormInput
                            id="broadcast-publication-time"
                            :value.sync="broadcast.publication_time"
                            type="datetime-local"
                            placeholder="Enter publication time"
                            required />
                    </BFormGroup>
                </BCol>
                <BCol>
                    <BFormGroup
                        id="broadcast-expiration-time-group"
                        label="Expiration Time"
                        label-for="broadcast-expiration-time"
                        description="The broadcast will not be displayed and will be deleted from the database after this time. Default is 6 months from the creation time.">
                        <BFormInput
                            id="broadcast-expiration-time"
                            v-model="broadcast.expiration_time"
                            type="datetime-local"
                            placeholder="Enter expiration time"
                            required />
                    </BFormGroup>
                </BCol>
            </BRow>

            <BRow align-v="center" class="m-1">
                <Heading size="md"> Preview </Heading>
            </BRow>

            <BroadcastContainer :broadcast="broadcast" preview-mode />

            <BRow class="m-2" align-h="center">
                <AsyncButton
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

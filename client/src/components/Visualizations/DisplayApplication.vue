<script setup lang="ts">
import { faExternalLinkAlt, faSpinner } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert } from "bootstrap-vue";
import { computed, onMounted, ref } from "vue";

import { type components, GalaxyApi } from "@/api";
import { errorMessageAsString } from "@/utils/simple-error";

import LoadingSpan from "@/components/LoadingSpan.vue";

type CreateLinkFeedback = components["schemas"]["CreateLinkFeedback"];

const TIMEOUT = 2000;

const props = defineProps({
    appName: {
        type: String,
        required: true,
    },
    datasetId: {
        type: String,
        required: true,
    },
    linkName: {
        type: String,
        required: true,
    },
});

const applicationData = ref<CreateLinkFeedback>({});
const errorMessage = ref("");
const isLoading = ref(true);

const hasData = computed(() => !!applicationData.value);
const hostUrl = computed(() => {
    if (applicationData.value?.resource) {
        try {
            return new URL(applicationData.value.resource).origin;
        } catch {
            return null;
        }
    }
    return null;
});

async function requestLink() {
    const { data, error } = await GalaxyApi().POST("/api/display_applications/create_link", {
        body: {
            app_name: props.appName,
            dataset_id: props.datasetId,
            link_name: props.linkName,
        },
    });
    if (error) {
        errorMessage.value = `Failed to create link: ${errorMessageAsString(error.err_msg)}`;
        console.error(error);
    } else {
        errorMessage.value = "";
        applicationData.value = data;
        if (applicationData.value.resource) {
            window.open(applicationData.value.resource, "_blank");
        } else if (applicationData.value.refresh) {
            setTimeout(() => requestLink(), TIMEOUT);
        }
    }
    isLoading.value = false;
}

onMounted(() => {
    requestLink();
});
</script>

<template>
    <div>
        <BAlert v-if="errorMessage" variant="danger" show>
            {{ errorMessage }}
        </BAlert>
        <LoadingSpan v-else-if="isLoading" />
        <div v-else-if="hasData">
            <div v-for="(message, messageIndex) in applicationData.messages" :key="messageIndex">
                <BAlert :variant="message[1]" show>
                    <FontAwesomeIcon v-if="applicationData.refresh" spin :icon="faSpinner" />
                    <span>{{ message[0] }}</span>
                </BAlert>
            </div>
            <div v-if="applicationData.preparable_steps">
                <h2>Preparation Status</h2>
                <table class="colored">
                    <tr>
                        <th>Step Name</th>
                        <th>Ready</th>
                        <th>Dataset Status</th>
                    </tr>
                    <tr v-for="(step, stepIndex) in applicationData.preparable_steps" :key="stepIndex">
                        <td>{{ step.name }}</td>
                        <td>{{ step.ready }}</td>
                        <td>{{ step.state }}</td>
                    </tr>
                </table>
            </div>
            <BAlert v-if="applicationData.resource" variant="info" show>
                <span>
                    <span>Display application is ready and can be viewed at</span>
                    <a :href="applicationData.resource" target="_blank">
                        <span>{{ hostUrl }}</span>
                        <FontAwesomeIcon :icon="faExternalLinkAlt" />
                    </a>
                </span>
            </BAlert>
        </div>
    </div>
</template>

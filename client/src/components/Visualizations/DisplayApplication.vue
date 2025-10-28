<script setup>
import axios from "axios";
import { BAlert } from "bootstrap-vue";
import { withPrefix } from "@/utils/redirect";
import LoadingSpan from "../LoadingSpan.vue";
import { computed, onMounted, ref } from "vue";
import { faSpinner } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { errorMessageAsString } from "@/utils/simple-error";

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

const applicationData = ref({});
const errorMessage = ref("");
const isLoading = ref(true);

const hasData = computed(() => !!applicationData.value);

async function requestLink() {
    const params = {
        app_name: props.appName,
        dataset_id: props.datasetId,
        link_name: props.linkName,
    }
    try {
        const buildUrl = withPrefix("/api/display_applications/create_link");
        const { data } = await axios.post(buildUrl, params);
        applicationData.value = data;
        if (applicationData.value.resource) {
            window.location.url = data.resource;
        } else if (applicationData.value.refresh) {
            setTimeout(() => requestLink(), TIMEOUT);
        }
        errorMessage.value = "";
    } catch (e) {
        errorMessage.value = `Failed to create link: ${errorMessageAsString(e)}.`;
        console.error(e);
    }
    isLoading.value = false;
}

onMounted(() => {
    requestLink();
});
</script>

<template>
    <BAlert v-if="errorMessage" variant="danger" show>
        {{ errorMessage }}
    </BAlert>
    <LoadingSpan v-else-if="isLoading" />
    <div v-else-if="hasData">
        <div v-for="(message, messageIndex) in applicationData.msg" :key="messageIndex">
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
    </div>
</template>

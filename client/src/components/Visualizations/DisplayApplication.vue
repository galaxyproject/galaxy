<script setup>
import { urlData } from "utils/url";
import { DatasetProvider } from "components/providers";
import { computed, defineProps, onMounted, ref } from "vue";
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
const hasData = computed(() => !!applicationData.value);
async function getCreateLink() {
    const params = new URLSearchParams({
        app_name: props.appName,
        dataset_id: props.datasetId,
        link_name: props.linkName,
    });
    const buildUrl = `/api/display_applications/create_link?${params.toString()}`;
    applicationData.value = await urlData({ url: buildUrl });
    console.log(applicationData.value);
}
onMounted(() => {
    getCreateLink();
});
</script>
<template>
    <div v-if="hasData">
        <div v-for="(message, messageIndex) in applicationData.msg" :key="messageIndex">
            <b-alert :variant="message[1]" show>{{ message[0] }}</b-alert>
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

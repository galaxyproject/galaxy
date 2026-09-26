<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed } from "vue";

import { isAdminUser } from "@/api";
import { useJobDestinationParametersStore } from "@/stores/jobDestinationParametersStore";
import { useUserStore } from "@/stores/userStore";

import Heading from "../Common/Heading.vue";

const { currentUser } = storeToRefs(useUserStore());
const jobDestinationParametersStore = useJobDestinationParametersStore();

interface Props {
    jobId: string;
}

const props = defineProps<Props>();

const jobDestinationParams = computed(() => {
    return jobDestinationParametersStore.getJobDestinationParams(props.jobId);
});
</script>

<template>
    <div v-if="isAdminUser(currentUser)">
        <Heading id="destination-parameters-heading" h2 separator inline size="md"> Destination Parameters </Heading>
        <table id="destination_parameters" class="tabletip info_data_table">
            <tbody>
                <tr v-for="(value, title) in jobDestinationParams" :key="title">
                    <td>{{ title }}</td>
                    <td>{{ value }}</td>
                </tr>
            </tbody>
        </table>
    </div>
</template>

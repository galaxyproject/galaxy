<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed } from "vue";

import { useJobDestinationParametersStore } from "@/stores/jobDestinationParametersStore";
import { useUserStore } from "@/stores/userStore";

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
    <div v-if="currentUser?.is_admin">
        <h2 class="h-md">Destination Parameters</h2>
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

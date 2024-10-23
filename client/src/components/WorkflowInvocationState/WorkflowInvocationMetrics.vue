<script setup lang="ts">
import { BCard } from "bootstrap-vue";
import { GalaxyApi, type components } from "@/api";
import { computed, ref, watch } from "vue";
import type JobMetrics from "../JobMetrics/JobMetrics.vue";
import { errorMessageAsString } from "@/utils/simple-error";
import MetricsBoxPlot from "./MetricsBoxPlots.vue";

const props = defineProps({
    invocationId: {
        type: String,
        required: true,
    },
});


const jobMetrics = ref<components["schemas"]["JobMetric"][]>()
const fetchError = ref<string>()

async function fetchMetrics() {
    const {data, error} = await GalaxyApi().GET("/api/invocations/{invocation_id}/metrics", {
        params: {
            path: {
                invocation_id: props.invocationId
            }
        }
    })
    console.log("data", data, error);
    if (error) {
        fetchError.value = errorMessageAsString(error)
    } else {
        jobMetrics.value = data
    }
}


watch((props), () => fetchMetrics(), { immediate: true })

const wallclock = computed(() => {
    return jobMetrics.value?.filter((jobMetric) => jobMetric.name == "runtime_seconds")
})

</script>

<template>
    <MetricsBoxPlot v-if="wallclock" :job-data="wallclock"/>
    <!--
    <div>
        {{ jobMetrics }}
    </div>  
    -->
</template>

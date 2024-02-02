<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faQuestionCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { ref } from "vue";

import { HistoryMetrics } from "@/api";
import { fetcher } from "@/api/schema";
import {
    worldwideCarbonIntensity,
    worldwidePowerUsageEffectiveness,
} from "@/components/CarbonEmissions/carbonEmissionConstants";
import { useConfig } from "@/composables/config";
import { useHistoryStore } from "@/stores/historyStore";

import CarbonEmissions from "@/components/CarbonEmissions/CarbonEmissions.vue";
import Heading from "@/components/Common/Heading.vue";

library.add(faQuestionCircle);

const props = defineProps({
    historyId: {
        type: String,
        required: true,
    },
});

const { getHistoryNameById } = useHistoryStore();
const { config } = useConfig(true);

const carbonIntensity = (config.value.carbon_intensity as number) ?? worldwideCarbonIntensity;
const geographicalServerLocationName = (config.value.geographical_server_location_name as string) ?? "GLOBAL";
const powerUsageEffectiveness = (config.value.power_usage_effectiveness as number) ?? worldwidePowerUsageEffectiveness;
const TODOcoresAllocated = 2;

const historyMetrics = ref<HistoryMetrics>({
    total_jobs_in_history: 0,
    total_runtime_in_seconds: 0,
    total_cores_allocated: 0,
    total_memory_allocated_in_mebibyte: 0,
});

fetcher
    .path("/api/histories/{history_id}/metrics")
    .method("get")
    .create()({ history_id: props.historyId })
    .then((res) => {
        if (res.ok) {
            historyMetrics.value = res.data;
        }
    });
</script>

<template>
    <div>
        <header>
            <Heading h1 bold class="my-3"> History Carbon Emissions </Heading>

            <p>
                Here is an estimated summary of the total carbon footprint of all datasets and jobs in the history:
                <strong>{{ getHistoryNameById(props.historyId) }}</strong
                >. These estimates can help you get a better sense of your history's carbon footprint which may
                ultimately serve as a motivation to use computing resources more responsibly.
            </p>

            <p>
                <router-link
                    to="/carbon_emissions_calculations"
                    title="Learn about how we estimate carbon emissions"
                    class="align-self-start mt-2">
                    <span>
                        Click here to learn more about how we calculate your carbon emissions data.
                        <FontAwesomeIcon icon="fa-question-circle" />
                    </span>
                </router-link>
            </p>
        </header>

        <hr class="py-2" />

        <CarbonEmissions
            :carbon-intensity="carbonIntensity"
            :geographical-server-location-name="geographicalServerLocationName"
            :power-usage-effectiveness="powerUsageEffectiveness"
            :job-runtime-in-seconds="historyMetrics?.total_runtime_in_seconds"
            :cores-allocated="TODOcoresAllocated"
            :memory-allocated-in-mebibyte="historyMetrics?.total_memory_allocated_in_mebibyte" />
    </div>
</template>

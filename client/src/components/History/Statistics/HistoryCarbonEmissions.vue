<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faQuestionCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { ref, watch } from "vue";

import { EnergyUsageSummary } from "@/api";
import { fetcher } from "@/api/schema";
import {
    worldwideCarbonIntensity,
    worldwidePowerUsageEffectiveness,
} from "@/components/CarbonEmissions/carbonEmissionConstants";
import { useCarbonEmissions } from "@/composables/carbonEmissions";

import CarbonEmissions from "@/components/CarbonEmissions/CarbonEmissions.vue";

library.add(faQuestionCircle);

const props = defineProps<{ historyId: string }>();

const { carbonIntensity, geographicalServerLocationName } = useCarbonEmissions();

const energyUsage = ref<EnergyUsageSummary>({
    total_energy_needed_cpu_kwh: 0,
    total_energy_needed_memory_kwh: 0,
    total_energy_needed_kwh: 0,
});

async function fetchEnergyUsageData() {
    const res = await fetcher.path("/api/histories/{history_id}/energy_usage").method("get").create()({
        history_id: props.historyId,
    });

    if (res.ok) {
        energyUsage.value = res.data;
    }
}

watch(
    () => props.historyId,
    () => fetchEnergyUsageData(),
    { immediate: true }
);
</script>

<template>
    <div>
        <CarbonEmissions
            :energy-needed-memory="energyUsage.total_energy_needed_memory_kwh"
            :energy-needed-c-p-u="energyUsage.total_energy_needed_cpu_kwh">
            <template v-slot:header>
                <p>
                    Here is an estimated summary of the total carbon footprint of all datasets and jobs in the current
                    history. These estimates can help you get a better sense of your history's carbon footprint which
                    may ultimately serve as a motivation to use computing resources more responsibly.
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
            </template>

            <template v-slot:footer>
                <p class="p-0 m-0">
                    <span v-if="geographicalServerLocationName === 'GLOBAL'" id="location-explanation">
                        <strong>1.</strong> Based off of the global carbon intensity value of
                        {{ worldwideCarbonIntensity }}.
                    </span>
                    <span v-else id="location-explanation">
                        <strong>1.</strong> based off of this galaxy instance's configured location of
                        <strong>{{ geographicalServerLocationName }}</strong
                        >, which has a carbon intensity value of {{ carbonIntensity }} gCO2/kWh.
                    </span>

                    <br />

                    <span id="pue">
                        <strong>2.</strong> Using the global default power usage effectiveness value of
                        {{ worldwidePowerUsageEffectiveness }}.
                    </span>
                </p>
            </template>
        </CarbonEmissions>
    </div>
</template>

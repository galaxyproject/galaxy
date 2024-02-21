<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faQuestionCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

import { worldwideCarbonIntensity } from "@/components/CarbonEmissions/carbonEmissionConstants";
import * as carbonEmissionsConstants from "@/components/CarbonEmissions/carbonEmissionConstants";
import { useConfig } from "@/composables/config";

import CarbonEmissions from "@/components/CarbonEmissions/CarbonEmissions.vue";
import Heading from "@/components/Common/Heading.vue";

library.add(faQuestionCircle);

const props = defineProps<{
    energyUsage: {
        energyNeededCPU: number;
        energyNeededMemory: number;
    };
    estimatedServerInstanceName: string;
}>();

const { config } = useConfig(true);
const carbonIntensity = (config.value.carbon_intensity as number) ?? worldwideCarbonIntensity;
const geographicalServerLocationName = (config.value.geographical_server_location_name as string) ?? "GLOBAL";
</script>

<template>
    <div class="mt-4">
        <CarbonEmissions
            :energy-needed-memory="props.energyUsage.energyNeededMemory"
            :energy-needed-c-p-u="props.energyUsage.energyNeededCPU">
            <template v-slot:header>
                <Heading h2 separator inline bold> Carbon Footprint </Heading>
            </template>

            <template v-slot:footer>
                <p class="p-0 m-0">
                    <span v-if="geographicalServerLocationName === 'GLOBAL'" id="location-explanation">
                        <strong>1.</strong> Based off of the global carbon intensity value of
                        {{ carbonEmissionsConstants.worldwideCarbonIntensity }}.
                    </span>
                    <span v-else id="location-explanation">
                        <strong>1.</strong> based off of this galaxy instance's configured location of
                        <strong>{{ geographicalServerLocationName }}</strong
                        >, which has a carbon intensity value of {{ carbonIntensity }} gCO2/kWh.
                    </span>

                    <br />

                    <span id="pue">
                        <strong>2.</strong> Using the global default power usage effectiveness value of
                        {{ carbonEmissionsConstants.worldwidePowerUsageEffectiveness }}.
                    </span>

                    <br />

                    <strong>3.</strong> based off of the closest AWS EC2 instance comparable to the server that ran this
                    job. Estimates depend on the core count, allocated memory and the job runtime. The closest estimate
                    is a <strong>{{ estimatedServerInstanceName }}</strong> instance.
                </p>

                <div class="mt-2">
                    <router-link
                        to="/carbon_emissions_calculations"
                        title="Learn about how we estimate carbon emissions">
                        <span>
                            Learn more about how we calculate your carbon emissions data.
                            <FontAwesomeIcon icon="fa-question-circle" />
                        </span>
                    </router-link>
                </div>
            </template>
        </CarbonEmissions>
    </div>
</template>

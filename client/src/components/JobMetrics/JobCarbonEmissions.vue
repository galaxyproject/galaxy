<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faQuestionCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, ref, unref } from "vue";

import { worldwideCarbonIntensity } from "@/components/CarbonEmissions/carbonEmissionConstants";
import * as carbonEmissionsConstants from "@/components/CarbonEmissions/carbonEmissionConstants";
import { useConfig } from "@/composables/config";

import CarbonEmissions from "@/components/CarbonEmissions/CarbonEmissions.vue";
import Heading from "@/components/Common/Heading.vue";

library.add(faQuestionCircle);

interface CarbonEmissionsProps {
    jobRuntimeInSeconds: number;
    coresAllocated: number;
    memoryAllocatedInMebibyte?: number;
    showHeader: boolean;
    showCarbonEmissionsCalculationsLink: boolean;
}

const props = withDefaults(defineProps<CarbonEmissionsProps>(), {
    memoryAllocatedInMebibyte: 0,
    showHeader: false,
    showCarbonEmissionsCalculationsLink: false,
});

const { config } = useConfig(true);

const carbonIntensity = (config.value.carbon_intensity as number) ?? worldwideCarbonIntensity;
const geographicalServerLocationName = (config.value.geographical_server_location_name as string) ?? "GLOBAL";
const powerUsageEffectiveness =
    (config.value.power_usage_effectiveness as number) ?? carbonEmissionsConstants.worldwidePowerUsageEffectiveness;

const carbonEmissions = computed(() => {
    if (!estimatedServerInstance.value) {
        return;
    }

    const memoryPowerUsed = carbonEmissionsConstants.memoryPowerUsage;
    const runtimeInHours = props.jobRuntimeInSeconds / (60 * 60); // Convert to hours
    const memoryAllocatedInGibibyte = props.memoryAllocatedInMebibyte / 1024; // Convert to gibibyte

    const cpuInfo = estimatedServerInstance.value.cpuInfo;
    const tdpPerCore = cpuInfo.tdp / cpuInfo.totalAvailableCores;
    const normalizedTdpPerCore = tdpPerCore * props.coresAllocated;

    // Power needed in Watt
    const powerNeededCpu = powerUsageEffectiveness * normalizedTdpPerCore;
    const powerNeededMemory = powerUsageEffectiveness * memoryAllocatedInGibibyte * memoryPowerUsed;
    const totalPowerNeeded = powerNeededCpu + powerNeededMemory;

    // Energy needed. Convert Watt to kWh
    const energyNeededCPU = (runtimeInHours * powerNeededCpu) / 1000;
    const energyNeededMemory = (runtimeInHours * powerNeededMemory) / 1000;
    const totalEnergyNeeded = (runtimeInHours * totalPowerNeeded) / 1000;

    // Carbon emissions (carbon intensity is in grams/kWh so emissions results are in grams of CO2)
    const cpuCarbonEmissions = energyNeededCPU * carbonIntensity;
    const memoryCarbonEmissions = energyNeededMemory * carbonIntensity;
    const totalCarbonEmissions = totalEnergyNeeded * carbonIntensity;

    return {
        cpuCarbonEmissions,
        memoryCarbonEmissions,
        totalCarbonEmissions,

        energyNeededCPU,
        energyNeededMemory,
        totalEnergyNeeded,
    };
});

const estimatedServerInstance = computed(() => {
    const ec2 = unref(ec2Instances);
    if (!ec2) {
        return;
    }

    const memory = props.memoryAllocatedInMebibyte;
    const adjustedMemory = memory ? memory / 1024 : 0;
    const cores = props.coresAllocated;

    const serverInstance = ec2.find((instance) => {
        if (adjustedMemory === 0) {
            // Exclude memory from search criteria
            return instance.vCpuCount >= cores;
        }

        // Search by all criteria
        return instance.mem >= adjustedMemory && instance.vCpuCount >= cores;
    });

    if (!serverInstance) {
        return;
    }

    const cpu = serverInstance.cpu[0];
    if (!cpu) {
        return;
    }

    return {
        name: serverInstance.name,
        cpuInfo: {
            modelName: cpu.cpuModel,
            totalAvailableCores: cpu.coreCount,
            tdp: cpu.tdp,
        },
    };
});

const ec2Instances = ref<EC2[]>();
import("@/components/JobMetrics/awsEc2ReferenceData.js").then((data) => (ec2Instances.value = data.ec2Instances));

type EC2 = {
    name: string;
    mem: number;
    price: number;
    priceUnit: string;
    vCpuCount: number;
    cpu: {
        cpuModel: string;
        tdp: number;
        coreCount: number;
        source: string;
    }[];
};
</script>

<template>
    <div v-if="carbonEmissions && estimatedServerInstance" class="mt-4">
        <CarbonEmissions
            :energy-needed-memory="carbonEmissions.energyNeededMemory"
            :energy-needed-c-p-u="carbonEmissions.energyNeededCPU"
            :total-energy-needed="carbonEmissions.totalEnergyNeeded"
            :total-carbon-emissions="carbonEmissions.totalCarbonEmissions">
            <template v-slot:header>
                <Heading v-if="props.showHeader" h2 separator inline bold> Carbon Footprint </Heading>
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

                    <span
                        v-if="powerUsageEffectiveness === carbonEmissionsConstants.worldwidePowerUsageEffectiveness"
                        id="pue">
                        <strong>2.</strong> Using the global default power usage effectiveness value of
                        {{ carbonEmissionsConstants.worldwidePowerUsageEffectiveness }}.
                    </span>
                    <span v-else id="pue">
                        <strong>2.</strong> using the galaxy instance's configured power usage effectiveness ratio value
                        of of {{ powerUsageEffectiveness }}.
                    </span>

                    <br />

                    <strong>3.</strong> based off of the closest AWS EC2 instance comparable to the server that ran this
                    job. Estimates depend on the core count, allocated memory and the job runtime. The closest estimate
                    is a <strong>{{ estimatedServerInstance.name }}</strong> instance.
                </p>

                <router-link
                    v-if="props.showCarbonEmissionsCalculationsLink"
                    to="/carbon_emissions_calculations"
                    title="Learn about how we estimate carbon emissions"
                    class="align-self-start mt-2">
                    <span>
                        Learn more about how we calculate your carbon emissions data.
                        <FontAwesomeIcon icon="fa-question-circle" />
                    </span>
                </router-link>
            </template>
        </CarbonEmissions>
    </div>
    <div v-else>Carbon emissions could not be computed at this time.</div>
</template>

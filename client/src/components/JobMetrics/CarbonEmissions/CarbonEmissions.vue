<script setup lang="ts">
import BarChart from "./BarChart.vue";
import CarbonEmissionsCard from "./CarbonEmissionCard.vue";
import { computed, unref } from "vue";
import { faQuestionCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import Heading from "@/components/Common/Heading.vue";
import { library } from "@fortawesome/fontawesome-svg-core";
import * as carbonEmissionsConstants from "./carbonEmissionConstants.js";
import type { GetComponentPropTypes } from "types/utilityTypes";

library.add(faQuestionCircle);

interface CarbonEmissionsProps {
    estimatedServerInstance: {
        name: string;
        cpuInfo: {
            modelName: string;
            totalAvailableCores: number;
            tdp: number;
        };
    };
    jobRuntimeInSeconds: number;
    coresAllocated: number;
    memoryAllocatedInMebibyte?: number;
}

const props = withDefaults(defineProps<CarbonEmissionsProps>(), {
    memoryAllocatedInMebibyte: 0,
});

const carbonEmissions = computed(() => {
    const powerUsageEffectiveness = carbonEmissionsConstants.worldwidePowerUsageEffectiveness;
    const memoryPowerUsed = carbonEmissionsConstants.memoryPowerUsage;
    const runtimeInHours = props.jobRuntimeInSeconds / (60 * 60); // Convert to hours
    const memoryAllocatedInGibibyte = props.memoryAllocatedInMebibyte / 1024; // Convert to gibibyte

    const cpuInfo = props.estimatedServerInstance.cpuInfo;
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
    const carbonIntensity = carbonEmissionsConstants.worldwideCarbonIntensity;
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

const carbonEmissionsComparisons = computed(() => {
    if (!carbonEmissions.value) {
        return;
    }

    const { totalCarbonEmissions, totalEnergyNeeded } = carbonEmissions.value;

    const {
        averagePassengerCarEmissionsEU,
        averagePassengerCarEmissionsUS,
        gasolineCarbonEmissionsPerGallon,
        lightbulbEnergyUsage,
        smartphonesChargedCarbonEmissions,
        treeYear,
    } = carbonEmissionsConstants;

    type CarbonComparison = {
        heading: string;
        explanation: string;
        value: string;
        icon: GetComponentPropTypes<typeof CarbonEmissionsCard>["icon"];
    };

    const gasolineConsumed: CarbonComparison = {
        heading: "Gasoline consumed",
        explanation: "The amount of gasoline consumed running this job",
        value: prettyPrintValue({
            // Multiply by 3.785 to convert gallons to litres
            value: parseFloat((totalCarbonEmissions / (gasolineCarbonEmissionsPerGallon * 3.785)).toFixed(2)),
            threshold: 1e-1,
            unit: "l",
        }),
        icon: "gasPump",
    };

    const drivingInEU: CarbonComparison = {
        heading: "Distance driven in EU",
        explanation: "Distance driven in km in the EU",
        value: prettyPrintValue({
            value: parseFloat((totalCarbonEmissions / averagePassengerCarEmissionsEU).toFixed(2)),
            threshold: 1e-1,
            unit: "km",
        }),
        icon: "car",
    };

    const drivingInUS: CarbonComparison = {
        heading: "Distance driven in US",
        explanation: "Distance driven in miles in the US",
        value: prettyPrintValue({
            value: parseFloat((totalCarbonEmissions / averagePassengerCarEmissionsUS).toFixed(2)),
            threshold: 1e-1,
            unit: "mile(s)",
        }),
        icon: "car",
    };

    const lightbulbsRunning: CarbonComparison = {
        heading: "Light bulbs running",
        explanation:
            "The amount of incandescent light bulbs you could have powered for one hour given your job's energy usage",
        value: prettyPrintValue({
            value: parseFloat((totalEnergyNeeded / lightbulbEnergyUsage).toFixed(3)),
            threshold: 1,
        }),
        icon: "lightbulb",
    };

    const smartphonesCharged: CarbonComparison = {
        heading: "Phones charged",
        explanation: "How many smartphones you could have charged given your job's energy usage",
        value: prettyPrintValue({
            value: parseFloat((totalCarbonEmissions / (smartphonesChargedCarbonEmissions * 1e6)).toFixed(2)),
            threshold: 1e-1 * 5, // at least one smartphone charged to 50%
        }),
        icon: "mobilePhone",
    };

    const treeMonths: CarbonComparison = {
        heading: "Tree months",
        explanation: "How long it would take a tree to sequester the carbon emissions from your job",
        value: prettyPrintValue({
            value: Math.round((totalCarbonEmissions / treeYear) * 12),
            threshold: 1e-1 * 5, // at least half of a month
        }),
        icon: "tree",
    };

    return [drivingInEU, drivingInUS, gasolineConsumed, lightbulbsRunning, smartphonesCharged, treeMonths];
});

const canShowMemory = computed(() => {
    return props.memoryAllocatedInMebibyte && props.memoryAllocatedInMebibyte !== 0;
});

const canShowMoreThanOneMetric = computed(() => {
    return unref(canShowMemory);
});

const barChartData = computed(() => {
    const values = carbonEmissions.value;
    if (!values) {
        return;
    }

    const data = [
        {
            name: "CPU",
            value: getPercentage(values.cpuCarbonEmissions, values.totalCarbonEmissions),
        },
    ];

    const canShowMemory = carbonEmissions.value?.memoryCarbonEmissions !== 0;
    if (canShowMemory) {
        data.push({
            name: "Memory",
            value: getPercentage(values.memoryCarbonEmissions, values.totalCarbonEmissions),
        });
    }

    return data;
});

function prettyPrintValue({
    value,
    threshold,
    unit,
}: {
    value: number;
    threshold: number;
    unit?: string;
    convertValue?: (input: number) => number;
}) {
    if (value < threshold) {
        return `≤ ${threshold}  ${unit ?? ""}`;
    }

    return `${value} ${unit ?? ""}`;
}

function getPercentage(value: number, total: number) {
    return Number(((value / total) * 100).toFixed(2));
}

function getCarbonEmissionsText(carbonEmissionsInGrams: number) {
    let adjustedCarbonEmissions = carbonEmissionsInGrams;
    let unitMagnitude = "g";

    if (carbonEmissionsInGrams === 0) {
        return "0 g CO2e";
    }

    if (carbonEmissionsInGrams >= 1e6) {
        adjustedCarbonEmissions /= 1e6;
        unitMagnitude = "t";
    } else if (carbonEmissionsInGrams >= 1e3 && carbonEmissionsInGrams < 1e6) {
        adjustedCarbonEmissions /= 1000;
        unitMagnitude = "kg";
    } else if (carbonEmissionsInGrams >= 1 && carbonEmissionsInGrams <= 999) {
        unitMagnitude = "g";
    } else if (carbonEmissionsInGrams < 1 && carbonEmissionsInGrams > 1e-4) {
        adjustedCarbonEmissions *= 1000;
        unitMagnitude = "mg";
    } else {
        adjustedCarbonEmissions *= 1e6;
        unitMagnitude = "μg";
    }

    const roundedValue = Math.round(adjustedCarbonEmissions);
    return `${roundedValue === 0 ? "< 1" : roundedValue} ${unitMagnitude} CO2e`;
}

function getEnergyNeededText(energyNeededInKiloWattHours: number) {
    let adjustedEnergyNeeded = energyNeededInKiloWattHours;
    let unitMagnitude = "kW⋅h";

    if (energyNeededInKiloWattHours === 0) {
        return "0 kW⋅h";
    }

    if (energyNeededInKiloWattHours >= 1e3) {
        adjustedEnergyNeeded /= 1000;
        unitMagnitude = "MW⋅h";
    } else if (energyNeededInKiloWattHours >= 1 && energyNeededInKiloWattHours <= 999) {
        unitMagnitude = "W⋅h";
    } else if (energyNeededInKiloWattHours < 1 && energyNeededInKiloWattHours > 1e-4) {
        adjustedEnergyNeeded *= 1000;
        unitMagnitude = "mW⋅h";
    } else {
        adjustedEnergyNeeded *= 1e6;
        unitMagnitude = "µW⋅h";
    }

    const roundedValue = Math.round(adjustedEnergyNeeded);
    return `${roundedValue === 0 ? "< 1" : roundedValue} ${unitMagnitude}`;
}
</script>

<template>
    <div v-if="carbonEmissions && carbonEmissionsComparisons" class="mt-4">
        <Heading h1 separator inline bold> Carbon Footprint </Heading>

        <section class="carbon-emission-values my-4">
            <div class="emissions-grid">
                <!-- Carbon Footprint Totals -->
                <CarbonEmissionsCard
                    :value="getCarbonEmissionsText(carbonEmissions.totalCarbonEmissions)"
                    :explanation="'Amount of GHGs with a similar global warming effect as CO2'"
                    :heading="'Carbon Emissions'"
                    :icon="'smog'" />

                <CarbonEmissionsCard
                    :value="getEnergyNeededText(carbonEmissions.totalEnergyNeeded)"
                    :explanation="'Total energy usage per hour'"
                    :heading="'Energy Usage'"
                    :icon="'bolt'" />

                <!-- Carbon Emission Comparison -->
                <CarbonEmissionsCard
                    v-for="{ heading, value, explanation, icon } in carbonEmissionsComparisons"
                    :key="heading"
                    :value="value"
                    :explanation="explanation"
                    :heading="heading"
                    :icon="icon" />
            </div>

            <div class="usage-ratios">
                <h3>Resource Usage Ratio</h3>

                <BarChart v-if="barChartData && canShowMoreThanOneMetric" :data="barChartData" />

                <table class="tabletip info_data_table mt-4">
                    <caption>
                        * Carbon emission and energy usage ratios per component.
                    </caption>

                    <thead>
                        <th>Component</th>
                        <th>Carbon Emissions <sup>1.</sup> <sup>2.</sup></th>
                        <th>Energy Usage <sup>1.</sup></th>
                    </thead>

                    <tbody>
                        <tr>
                            <td>CPU</td>
                            <td id="cpu-carbon-emissions">
                                {{ getCarbonEmissionsText(carbonEmissions.cpuCarbonEmissions) }}
                            </td>
                            <td id="cpu-energy-usage">{{ getEnergyNeededText(carbonEmissions.energyNeededCPU) }}</td>
                        </tr>

                        <tr v-if="canShowMemory">
                            <td>Memory</td>
                            <td id="memory-carbon-emissions">
                                {{ getCarbonEmissionsText(carbonEmissions.memoryCarbonEmissions) }}
                            </td>
                            <td id="memory-energy-usage">
                                {{ getEnergyNeededText(carbonEmissions.energyNeededMemory) }}
                            </td>
                        </tr>
                    </tbody>
                </table>

                <p class="p-0 m-0">
                    <strong>1.</strong> based off of the closest AWS EC2 instance comparable to the server that ran this
                    job. Estimates depend on the core count, allocated memory and the job runtime. The closest estimate
                    is a <strong>{{ estimatedServerInstance.name }}</strong> instance.

                    <br />

                    <strong>2.</strong> CO2e represents other types of greenhouse gases the have similar global warming
                    potential as a metric unit amount of CO2 itself.

                    <br />
                </p>

                <router-link
                    to="/carbon_emissions_calculations"
                    title="Learn about how we estimate carbon emissions"
                    class="align-self-start mt-2">
                    <span>
                        Learn more about how we calculate your carbon emissions data.
                        <font-awesome-icon icon="fa-question-circle" />
                    </span>
                </router-link>
            </div>
        </section>
    </div>
</template>

<style scoped>
.usage-ratios {
    display: flex;
    flex-direction: column;
    align-items: center;
    align-self: center;
}

.carbon-emission-values {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(450px, 1fr));
    gap: 1rem;
}

.emissions-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    grid-gap: 1rem;
}
</style>

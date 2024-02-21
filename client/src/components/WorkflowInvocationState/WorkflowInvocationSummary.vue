<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";

import { EnergyUsageSummary } from "@/api";
import { fetcher } from "@/api/schema";
import {
    worldwideCarbonIntensity,
    worldwidePowerUsageEffectiveness,
} from "@/components/CarbonEmissions/carbonEmissionConstants";
import { useConfig } from "@/composables/config";
import { getRootFromIndexLink } from "@/onload";

import CarbonEmissions from "@/components/CarbonEmissions/CarbonEmissions.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import ProgressBar from "@/components/ProgressBar.vue";
import InvocationMessage from "@/components/WorkflowInvocationState/InvocationMessage.vue";

const getUrl = (path: any) => getRootFromIndexLink() + path;

const { config } = useConfig(true);
const carbonIntensity = config.value.carbon_intensity ?? worldwideCarbonIntensity;
const geographicalServerLocationName = config.value.geographical_server_location_name ?? "GLOBAL";

const energyUsage = ref<EnergyUsageSummary>({
    total_energy_needed_cpu_kwh: 0,
    total_energy_needed_memory_kwh: 0,
    total_energy_needed_kwh: 0,
});

const props = defineProps({
    invocation: {
        type: Object,
        required: true,
    },
    invocationAndJobTerminal: {
        type: Boolean,
        required: true,
    },
    invocationSchedulingTerminal: {
        type: Boolean,
        required: true,
    },
    jobStatesSummary: {
        type: Object,
        required: false,
        default: null,
    },
    index: {
        type: Number,
        required: false,
        default: null,
    },
});

const reportTooltip = "View report for this workflow invocation";
const generatePdfTooltip = "Generate PDF report for this workflow invocation";

const invocationId = computed(() => {
    return props.invocation?.id;
});

const indexStr = computed(() => {
    if (!props.index) {
        return "";
    }
    return `${props.index + 1}`;
});

const invocationState = computed(() => {
    return props.invocation?.state || "new";
});

const invocationStateSuccess = computed(() => {
    return invocationState.value === "scheduled" && runningCount.value === 0 && props.invocationAndJobTerminal;
});

const disabledReportTooltip = computed(() => {
    const state = invocationState.value;
    const runCount = runningCount.value;

    if (invocationState.value != "scheduled") {
        return `This workflow is not currently scheduled. The current state is  ${state}. Once the workflow is fully scheduled and jobs have complete this option will become available.`;
    }

    if (runCount != 0) {
        return `The workflow invocation still contains ${runCount} running job(s). Once these jobs have completed this option will become available.`;
    }

    return "Steps for this workflow are still running. A report will be available once complete.";
});

const stepCount = computed(() => {
    return props.invocation?.steps.length;
});

const stepStates = computed(() => {
    const stepStates: any = {};
    if (!props.invocation) {
        return {};
    }

    for (const step of props.invocation.steps) {
        if (!stepStates[step.state]) {
            stepStates[step.state] = 1;
        } else {
            stepStates[step.state] += 1;
        }
    }
    return stepStates;
});

const invocationLink = computed(() => {
    return getUrl(`workflows/invocations/report?id=${invocationId.value}`);
});

const invocationPdfLink = computed(() => {
    return getUrl(`api/invocations/${invocationId.value}/report.pdf`);
});

const stepStatesStr = computed(() => {
    return `${stepStates.value?.scheduled || 0} of ${stepCount.value} steps successfully scheduled.`;
});

const jobCount = computed(() => {
    return !props.jobStatesSummary ? null : props.jobStatesSummary.jobCount();
});

const jobStatesStr = computed(() => {
    let jobStr = `${props.jobStatesSummary?.numTerminal() || 0} of ${jobCount.value} jobs complete`;
    if (!props.invocationSchedulingTerminal) {
        jobStr += " (total number of jobs will change until all steps fully scheduled)";
    }
    return `${jobStr}.`;
});

const runningCount = computed(() => {
    return countStates(["running"]);
});
const okCount = computed(() => {
    return countStates(["ok", "skipped"]);
});
const errorCount = computed(() => {
    return countStates(["error", "deleted"]);
});
const newCount = computed(() => {
    return jobCount.value - okCount.value - runningCount.value - errorCount.value;
});

const emit = defineEmits(["invocation-cancelled"]);

function onCancel() {
    emit("invocation-cancelled");
}

function countStates(states: string[]) {
    let count = 0;
    if (props.jobStatesSummary && props.jobStatesSummary.hasDetails()) {
        for (const state of states) {
            count += props.jobStatesSummary.states()[state] || 0;
        }
    }
    return count;
}

async function fetchEnergyUsageData() {
    const res = await fetcher.path("/api/invocations/{invocation_id}/energy_usage").method("get").create()({
        invocation_id: props.invocation?.id,
    });

    if (res.ok) {
        energyUsage.value = res.data;
    }
}

onMounted(() => {
    fetchEnergyUsageData();
});

watch(
    () => props.invocation,
    () => {
        fetchEnergyUsageData();
    },
    {
        deep: true,
    }
);
</script>

<template>
    <div class="mb-3 workflow-invocation-state-component">
        <div v-if="invocationAndJobTerminal">
            <span>
                <b-button
                    v-b-tooltip.hover
                    :title="invocationStateSuccess ? reportTooltip : disabledReportTooltip"
                    :disabled="!invocationStateSuccess"
                    size="sm"
                    class="invocation-report-link"
                    :href="invocationLink">
                    View Report
                </b-button>
                <b-button
                    v-b-tooltip.hover
                    :title="invocationStateSuccess ? generatePdfTooltip : disabledReportTooltip"
                    :disabled="!invocationStateSuccess"
                    size="sm"
                    class="invocation-pdf-link"
                    :href="invocationPdfLink"
                    target="_blank">
                    Generate PDF
                </b-button>
            </span>
        </div>
        <div v-else-if="!invocationAndJobTerminal">
            <b-alert variant="info" show>
                <LoadingSpan :message="`Waiting to complete invocation ${indexStr}`" />
            </b-alert>
            <span
                v-b-tooltip.hover
                class="fa fa-times cancel-workflow-scheduling"
                title="Cancel scheduling of workflow invocation"
                @click="onCancel"></span>
        </div>
        <ProgressBar v-if="!stepCount" note="Loading step state summary..." :loading="true" class="steps-progress" />
        <template v-if="invocation.messages?.length">
            <InvocationMessage
                v-for="message in invocation.messages"
                :key="message.reason"
                class="steps-progress my-1"
                :invocation-message="message"
                :invocation="invocation">
            </InvocationMessage>
        </template>
        <ProgressBar
            v-else-if="invocationState == 'cancelled'"
            note="Invocation scheduling cancelled - expected jobs and outputs may not be generated."
            :error-count="1"
            class="steps-progress" />
        <ProgressBar
            v-else-if="invocationState == 'failed'"
            note="Invocation scheduling failed - Galaxy administrator may have additional details in logs."
            :error-count="1"
            class="steps-progress" />
        <ProgressBar
            v-else
            :note="stepStatesStr"
            :total="stepCount"
            :ok-count="stepStates.scheduled"
            :loading="!invocationSchedulingTerminal"
            class="steps-progress" />
        <ProgressBar
            :note="jobStatesStr"
            :total="jobCount"
            :ok-count="okCount"
            :running-count="runningCount"
            :new-count="newCount"
            :error-count="errorCount"
            :loading="!invocationAndJobTerminal"
            class="jobs-progress" />

        <div>
            <strong>Carbon Emissions:</strong>

            <CarbonEmissions
                :energy-needed-memory="energyUsage.total_energy_needed_memory_kwh"
                :energy-needed-c-p-u="energyUsage.total_energy_needed_cpu_kwh">
                <template v-slot:header>
                    <p>
                        Here is an estimated summary of the total carbon footprint of this workflow invocation.

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
    </div>
</template>

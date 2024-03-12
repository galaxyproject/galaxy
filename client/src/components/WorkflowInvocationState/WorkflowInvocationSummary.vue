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

        <div v-if="shouldShowCarbonEmissionsReports">
            <strong>Carbon Emissions:</strong>

            <CarbonEmissions
                :energy-needed-memory="energyUsage.total_energy_needed_memory_kwh"
                :energy-needed-c-p-u="energyUsage.total_energy_needed_cpu_kwh"
                :total-energy-needed="energyUsage.total_energy_needed_kwh"
                :total-carbon-emissions="() => energyUsage.total_energy_needed_kwh * carbonIntensity">
                <template v-slot:header>
                    <p>
                        Here is an estimated summary of the total carbon footprint of this workflow invocation.

                        <RouterLink
                            to="/carbon_emissions_calculations"
                            title="Learn about how we estimate carbon emissions"
                            class="align-self-start mt-2">
                            <span>
                                Click here to learn more about how we calculate your carbon emissions data.
                                <FontAwesomeIcon icon="fa-question-circle" />
                            </span>
                        </RouterLink>
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
<script>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faQuestionCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import CarbonEmissions from "components/CarbonEmissions/CarbonEmissions";
import mixin from "components/JobStates/mixin";
import LoadingSpan from "components/LoadingSpan";
import ProgressBar from "components/ProgressBar";
import { getRootFromIndexLink } from "onload";
import { computed, ref, watch } from "vue";
import { RouterLink } from "vue-router";

import { fetcher } from "@/api/schema";
import {
    worldwideCarbonIntensity,
    worldwidePowerUsageEffectiveness,
} from "@/components/CarbonEmissions/carbonEmissionConstants";
import { useCarbonEmissions } from "@/composables/carbonEmissions";

import InvocationMessage from "@/components/WorkflowInvocationState/InvocationMessage.vue";

library.add(faQuestionCircle);

const getUrl = (path) => getRootFromIndexLink() + path;

export default {
    components: {
        CarbonEmissions,
        FontAwesomeIcon,
        InvocationMessage,
        LoadingSpan,
        ProgressBar,
        RouterLink,
    },
    mixins: [mixin],
    props: {
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
    },
    setup(props) {
        const { 
            carbonIntensity,
            geographicalServerLocationName,
            shouldShowCarbonEmissionsReports
        } = useCarbonEmissions();

        const invocationId = computed(() => props.invocation?.id);

        const energyUsage = ref({
            total_energy_needed_cpu_kwh: 0,
            total_energy_needed_memory_kwh: 0,
            total_energy_needed_kwh: 0,
        });

        async function fetchEnergyUsageData() {
            const res = await fetcher.path("/api/invocations/{invocation_id}/metrics").method("get").create()({
                invocation_id: invocationId.value,
            });

            if (res.ok) {
                const { total_energy_needed_cpu_kwh, total_energy_needed_memory_kwh, total_energy_needed_kwh } =
                    res.data;

                energyUsage.value = {
                    total_energy_needed_cpu_kwh,
                    total_energy_needed_memory_kwh,
                    total_energy_needed_kwh,
                };
            }
        }

        watch(
            () => invocationId.value,
            () => {
                if (shouldShowCarbonEmissionsReports && invocationId.value) {
                    fetchEnergyUsageData();
                }
            },
            { immediate: true }
        );

        return {
            carbonIntensity,
            energyUsage,
            geographicalServerLocationName,
            shouldShowCarbonEmissionsReports,
            invocationId,
            worldwideCarbonIntensity,
            worldwidePowerUsageEffectiveness,
        };
    },
    data() {
        return {
            stepStatesInterval: null,
            jobStatesInterval: null,
            reportTooltip: "View report for this workflow invocation",
            generatePdfTooltip: "Generate PDF report for this workflow invocation",
        };
    },
    computed: {
        indexStr() {
            if (this.index == null) {
                return "";
            } else {
                return `${this.index + 1}`;
            }
        },
        invocationState: function () {
            return this.invocation?.state || "new";
        },
        invocationStateSuccess: function () {
            return this.invocationState == "scheduled" && this.runningCount === 0 && this.invocationAndJobTerminal;
        },
        disabledReportTooltip: function () {
            const state = this.invocationState;
            const runCount = this.runningCount;
            if (this.invocationState != "scheduled") {
                return (
                    "This workflow is not currently scheduled. The current state is ",
                    state,
                    ". Once the workflow is fully scheduled and jobs have complete this option will become available."
                );
            } else if (runCount != 0) {
                return (
                    "The workflow invocation still contains ",
                    runCount,
                    " running job(s). Once these jobs have completed this option will become available. "
                );
            } else {
                return "Steps for this workflow are still running. A report will be available once complete.";
            }
        },
        stepCount: function () {
            return this.invocation?.steps.length;
        },
        stepStates: function () {
            const stepStates = {};
            if (!this.invocation) {
                return {};
            }
            for (const step of this.invocation.steps) {
                if (!stepStates[step.state]) {
                    stepStates[step.state] = 1;
                } else {
                    stepStates[step.state] += 1;
                }
            }
            return stepStates;
        },
        invocationLink: function () {
            return getUrl(`workflows/invocations/report?id=${this.invocationId}`);
        },
        invocationPdfLink: function () {
            return getUrl(`api/invocations/${this.invocationId}/report.pdf`);
        },
        stepStatesStr: function () {
            return `${this.stepStates.scheduled || 0} of ${this.stepCount} steps successfully scheduled.`;
        },
        jobStatesStr: function () {
            let jobStr = `${this.jobStatesSummary?.numTerminal() || 0} of ${this.jobCount} jobs complete`;
            if (!this.invocationSchedulingTerminal) {
                jobStr += " (total number of jobs will change until all steps fully scheduled)";
            }
            return `${jobStr}.`;
        },
    },
    methods: {
        onCancel() {
            this.$emit("invocation-cancelled");
        },
    },
};
</script>

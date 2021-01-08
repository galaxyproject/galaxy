<template>
    <b-card header-tag="header" body-class="p-0">
        <template #header>
            <div class="mb-0 font-weight-bold">Validation Results</div>
            <div v-if="showFixAll">
                <a href="#" @click="autoFixAll">Attempt to fix any issue that can be automatically fixed.</a>
            </div>
        </template>
        <b-card-body>
            <div class="mb-2">
                <div v-if="parametersOkay">
                    <font-awesome-icon icon="check" class="text-success" />
                    <span>Workflow parameters are using formal inputs.</span>
                </div>
                <div v-else>
                    <font-awesome-icon icon="exclamation-triangle" class="text-warning" />
                    <span>
                        This workflow uses implicit workflow parameters. They should be replaced with
                        formal workflow inputs:
                    </span>
                    <div v-for="(item, idx) in legacyParametersArray" :key="idx">
                        <tt>{{ item.name }} </tt>
                    </div>
                </div>
            </div>

            <div class="mb-2">
                <div v-if="disconnectInputsOkay">
                    <font-awesome-icon icon="check" class="text-success" />
                    <span>All non-optional inputs to workflow steps are connected to formal workflow inputs.</span>
                </div>
                <div else>
                    <font-awesome-icon icon="exclamation-triangle" class="text-warning" />
                    <span>Some non-optional inputs are not connected to formal workflow inputs:</span>
                    <ul class="mt-2">
                        <li
                            v-for="(input, idx) in disconnectedInputs"
                            :key="idx"
                            @mouseover="highlight(input.stepId)"
                            @mouseleave="unhighlight(input.stepId)"
                            class="ml-2"
                        >
                            <a href="#" @click="scrollTo(input.stepId)" class="scrolls">
                                <i :class="input.stepIconClass" />{{ input.stepLabel }}: {{ input.inputLabel }}
                            </a>
                        </li>
                    </ul>
                </div>
            </div>

            <div v-if="inputsMetadataOkay">
                All workflow inputs have labels and annotations.
            </div>
            <div v-else>
                <p>
                    Some workflow inputs are missing labels and/or annotations.
                </p>
                <ul>
                    <li
                        v-for="(input, idx) in inputsMissingMetadata"
                        :key="idx"
                        @mouseover="highlight(input.stepId)"
                        @mouseleave="unhighlight(input.stepId)"
                    >
                        <b @click="scrollTo(input.stepId)" class="scrolls"
                            ><i :class="input.stepIconClass" />{{ input.stepLabel }}</b
                        >
                        <em class="small">
                            <span class="input-missing-metadata-summary">
                                This input is {{ missingSummary(input) }}.
                            </span>
                        </em>
                    </li>
                </ul>
            </div>

            <div v-if="outputsOkay">
                This workflow has outputs and they all have valid labels.
            </div>
            <div v-else-if="outputs.length == 0">
                This workflow has no labeled outputs, please select and label at least one output.

                <em class="small">
                    <p>
                        Formal, labeled outputs make tracking workflow provenance, usage within
                        subworkflows, and executing the workflow via the Galaxy API all more robust.
                    </p>
                </em>
            </div>
            <div v-else>
                <p>
                    The following workflow outputs have no labels, they should be assigned a useful label or
                    unchecked in the workflow editor to mark them as no longer being a workflow output.
                    Alternatively,
                    <a href="#" @click="removeUnlabeledWorkflowOutputs"
                        >click here <font-awesome-icon icon="cog"
                    /></a>
                    to remove these all as workflow outputs.
                </p>
                <ul>
                    <li
                        v-for="(output, idx) in unlabeledOutputs"
                        :key="idx"
                        @mouseover="highlight(output.stepId)"
                        @mouseleave="unhighlight(output.stepId)"
                    >
                        <b @click="scrollTo(output.stepId)" class="scrolls"
                            ><i :class="output.stepIconClass" />{{ output.stepLabel }}</b
                        >
                        <span class="unlabeled-output-name">
                            {{ output.outputName }}
                        </span>
                    </li>
                </ul>
            </div>

            <span>
                <div v-if="annotationOkay">
                    <p>
                        This workflow defines an annotation. Ideally, this helps the executors of the workflow
                        understand the purpose and usage of the workflow.
                    </p>
                </div>
                <div v-else>
                    <p>
                        <a href="#" @click="onAttributes"
                            ><font-awesome-icon icon="pencil-alt" />Edit workflow attributes</a
                        >
                        to add an annotation.
                    </p>
                    <em class="small">
                        <p>
                            This workflow does not define an annotation. This should provided to help the
                            executors of the workflow understand the purpose and usage of the workflow.
                        </p>
                    </em>
                </div>
            </span>
            <span>
                <div v-if="licenseOkay">
                    <p>
                        This workflow defines a license.
                    </p>
                </div>
                <div v-else>
                    <p>
                        <a href="#" @click="onAttributes"
                            ><font-awesome-icon icon="pencil-alt" />Edit workflow attributes</a
                        >
                        to specify a license.
                    </p>
                    <em class="small">
                        <p>
                            This workflow does not specify a license. This is important metadata for workflows
                            that will be published and/or shared to help workflow executors understand how it
                            may be used.
                        </p>
                    </em>
                </div>
            </span>
            <span>
                <div v-if="creatorOkay">
                    <p>
                        This workflow defines creator information.
                    </p>
                </div>
                <div v-else>
                    <p>
                        <a href="#" @click="onAttributes"
                            ><font-awesome-icon icon="pencil-alt" />Edit workflow attributes</a
                        >
                        to specify creator(s).
                    </p>
                    <em class="small">
                        <p>
                            This workflow does not specify creator(s). This is important metadata for workflows
                            that will be published and/or shared to help workflow executors know how to cite the
                            workflow authors.
                        </p>
                    </em>
                </div>
            </span>
        </b-card-body>
    </b-card>
</template>

<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import { LegacyParameters } from "components/Workflow/Editor/modules/utilities";
import { getDisconnectedInputs, getInputsMissingMetadata, getWorkflowOutputs } from "./modules/utilities";

Vue.use(BootstrapVue);

import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCog, faPencilAlt, faCheck, faTimes, faExclamationTriangle } from "@fortawesome/free-solid-svg-icons";

library.add(faCog);
library.add(faTimes);
library.add(faCheck);
library.add(faPencilAlt);
library.add(faExclamationTriangle);

export default {
    components: {
        FontAwesomeIcon,
    },
    props: {
        legacyParameters: {
            type: LegacyParameters,
        },
        nodes: {
            type: Object,
        },
        annotation: {
            type: String,
            default: "",
        },
        license: {
            type: String,
            default: "",
        },
        creator: {
            default: null,
        },
    },
    data() {
        return {
            whyInputs:
                "Formal inputs make tracking workflow provenance, usage within subworkflows, and executing the workflow via the Galaxy API all more robust.",
            forceRefresh: 0,
        };
    },
    methods: {
        refresh() {
            this.forceRefresh += 1;
        },
        extractLegacyParameter(item) {
            const actions = [
                {
                    action_type: "extract_legacy_parameter",
                    name: item.name,
                },
            ];
            this.$emit("refactor", actions);
        },
        extractWorkflowInput(disconnectedInput) {
            // convert step input into a workflow input connected to the step
            const actions = [
                {
                    action_type: "extract_input",
                    input: {
                        order_index: parseInt(disconnectedInput.stepId),
                        input_name: disconnectedInput.inputName,
                    },
                },
            ];
            this.$emit("refactor", actions);
        },
        removeUnlabeledWorkflowOutputs() {
            const actions = [{ action_type: "remove_unlabeled_workflow_outputs" }];
            this.$emit("refactor", actions);
        },
        onAttributes() {
            this.$emit("onAttributes");
        },
        missingSummary(input) {
            if (input.missingLabel && input.missingAnnotation) {
                return "missing a label and annotation";
            } else if (input.missingLabel) {
                return "missing a label";
            } else {
                return "missing an annotation";
            }
        },
        scrollTo(stepId) {
            this.$emit("scrollTo", this.nodes[parseInt(stepId)]);
        },
        highlight(stepId) {
            this.nodes[parseInt(stepId)].onHighlight();
        },
        unhighlight(stepId) {
            this.nodes[parseInt(stepId)].onUnhighlight();
        },
        autoFixAll() {
            const actions = [];
            if (!this.parametersOkay) {
                for (const legacyParameter of this.legacyParametersArray) {
                    if (legacyParameter.canExtract) {
                        actions.push({
                            action_type: "extract_legacy_parameter",
                            name: legacyParameter.name,
                        });
                    }
                }
            }
            if (!this.disconnectInputsOkay) {
                for (const disconnectedInput of this.disconnectedInputs) {
                    if (disconnectedInput.canExtract) {
                        actions.push({
                            action_type: "extract_input",
                            input: {
                                order_index: parseInt(disconnectedInput.stepId),
                                input_name: disconnectedInput.inputName,
                            },
                        });
                    }
                }
            }
            if (!this.outputsOkay) {
                actions.push({ action_type: "remove_unlabeled_workflow_outputs" });
            }
            this.$emit("refactor", actions);
        },
    },
    computed: {
        parametersOkay() {
            return this.legacyParameters == null || this.legacyParameters.parameters.length == 0;
        },
        disconnectInputsOkay() {
            return this.disconnectedInputs == null || this.disconnectedInputs.length == 0;
        },
        inputsMetadataOkay() {
            return this.inputsMissingMetadata.length == 0;
        },
        annotationOkay() {
            return !!this.annotation;
        },
        outputsOkay() {
            // console.log(this.outputs);
            return this.outputs.length > 0 && this.unlabeledOutputs.length == 0;
        },
        licenseOkay() {
            return !!this.license;
        },
        creatorOkay() {
            if (this.creator instanceof Array) {
                return this.creator.length > 0;
            } else {
                return !!this.creator;
            }
        },
        legacyParametersArray() {
            return this.legacyParameters ? this.legacyParameters.parameters : [];
        },
        // I tried to make these purely reactive but I guess it is not surprising that the
        // entirity of the nodes object and children aren't all purely reactive.
        // https://logaretm.com/blog/2019-10-11-forcing-recomputation-of-computed-properties/
        disconnectedInputs() {
            this.forceRefresh;
            return getDisconnectedInputs(this.nodes);
        },
        outputs() {
            this.forceRefresh;
            return getWorkflowOutputs(this.nodes);
        },
        inputsMissingMetadata() {
            this.forceRefresh;
            return getInputsMissingMetadata(this.nodes);
        },
        unlabeledOutputs() {
            const unlabeledOutputs = [];
            for (const output of this.outputs) {
                if (output.outputLabel == null) {
                    unlabeledOutputs.push(output);
                }
            }
            return unlabeledOutputs;
        },
        showFixAll() {
            // we could be even more percise here and check the inputs and such, because
            // of these extractions may not be possible.
            return !this.parametersOkay || !this.disconnectInputsOkay || !this.outputsOkay;
        },
    },
};
</script>

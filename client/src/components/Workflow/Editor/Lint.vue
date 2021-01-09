<template>
    <b-card header-tag="header" body-class="p-0">
        <template #header>
            <div class="mb-0 font-weight-bold">Validation Results</div>
            <div v-if="showFixAll">
                <a href="#" @click="autoFixAll">Attempt to fix any issue that can be automatically fixed.</a>
            </div>
        </template>
        <b-card-body>
            <LintSection
                :okay="parametersOkay"
                success-message="Workflow parameters are using formal inputs."
                warning-message="This workflow uses implicit workflow parameters. They should be replaced with
                formal workflow inputs:"
                :warning-items="legacyParametersArray"
                @onMouseOver="highlight"
                @onMouseLeave="unhighlight"
                @onClick="scrollTo"
            />

            <LintSection
                :okay="disconnectInputsOkay"
                success-message="All non-optional inputs to workflow steps are connected to formal workflow inputs."
                warning-message="Some non-optional inputs are not connected to formal workflow inputs:"
                :warning-items="disconnectedInputs"
                @onMouseOver="highlight"
                @onMouseLeave="unhighlight"
                @onClick="scrollTo"
            />

            <LintSection
                :okay="inputsMetadataOkay"
                success-message="All workflow inputs have labels and annotations."
                warning-message="Some workflow inputs are missing labels and/or annotations:"
                :warning-items="inputsMissingMetadata"
                @onMouseOver="highlight"
                @onMouseLeave="unhighlight"
                @onClick="scrollTo"
            />

            <LintSection
                :okay="outputsOkay"
                success-message="This workflow has outputs and they all have valid labels."
                warning-message="The following workflow outputs have no labels, they should be assigned a useful label or
                    unchecked in the workflow editor to mark them as no longer being a workflow output:"
                :warning-items="unlabeledOutputs"
                @onMouseOver="highlight"
                @onMouseLeave="unhighlight"
                @onClick="scrollTo"
            />

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
import LintSection from "components/Workflow/Editor/LintSection";
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
        LintSection,
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

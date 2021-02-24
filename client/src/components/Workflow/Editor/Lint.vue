<template>
    <b-container>
        <b-row>
            <b-col>
                <h4>Workflow Best Practices</h4>
            </b-col>
        </b-row>
        <b-row>
            <b-col>
                <div v-if="showFixAll">
                    <a href="#" @click="autoFixAll">Attempt to fix any issue that can be automatically fixed.</a>
                </div>
                <LintSection :okay="parametersOkay" title="Parameters" collapse-id="c-parameters">
                    <span>
                        <div v-if="parametersOkay">
                            <p>All workflow parameters (if any are defined) are using formal inputs.{{ whyInputs }}</p>
                        </div>
                        <div else>
                            <ul>
                                <li v-for="(item, idx) in legacyParametersArray" :key="idx">
                                    {{ item.name }}
                                    <font-awesome-icon
                                        v-if="item.canExtract"
                                        icon="cog"
                                        v-b-tooltip.hover
                                        title="Attempt to create a workflow input connected to this legacy parameter."
                                        @click="extractLegacyParameter(item)"
                                    />
                                </li>
                            </ul>
                            <em class="small">
                                <p>
                                    This workflow uses older-style implicit Galaxy workflow parameters (e.g. defining
                                    <tt>${parameter}</tt> on tool steps in the workflows). These should be replaced with
                                    formal workflow inputs. {{ whyInputs }}
                                </p>
                                <p>
                                    Many such legacy workflow parameters can be automatically converted to formal input
                                    steps by Galaxy, click the <font-awesome-icon icon="cog" /> to have Galaxy attempt
                                    this.
                                </p>
                            </em>
                        </div>
                    </span>
                </LintSection>
                <LintSection
                    :okay="disconnectInputsOkay"
                    title="Disconnected Inputs"
                    collapse-id="c-disconnected-inputs"
                >
                    <span>
                        <div v-if="disconnectInputsOkay">
                            All non-optional inputs to workflow steps are connected to formal workflow inputs.
                            {{ whyInputs }}
                        </div>
                        <div else>
                            <ul>
                                <li
                                    v-for="(input, idx) in disconnectedInputs"
                                    :key="idx"
                                    @mouseover="highlight(input.stepId)"
                                    @mouseleave="unhighlight(input.stepId)"
                                >
                                    <b @click="scrollTo(input.stepId)" class="scrolls"
                                        ><i :class="input.stepIconClass" />{{ input.stepLabel }}</b
                                    >
                                    <span class="disconnected-input-name">
                                        {{ input.inputLabel }}
                                        <font-awesome-icon
                                            v-if="input.canExtract"
                                            icon="cog"
                                            v-b-tooltip.hover
                                            title="Attempt to create a workflow input connected to this step input."
                                            @click="extractWorkflowInput(input)"
                                        />
                                    </span>
                                </li>
                            </ul>
                            <em class="small">
                                <p>
                                    Inputs to tool and subworkflow steps should be connected to formal workflow inputs.
                                    {{ whyInputs }}
                                </p>
                                <p>
                                    Most such step inputs can be automatically connected via Galaxy, click the
                                    <font-awesome-icon icon="cog" /> for inputs to have Galaxy attempt this.
                                </p>
                            </em>
                        </div>
                    </span>
                </LintSection>
                <LintSection :okay="inputsMetadataOkay" title="Input Metadata" collapse-id="c-input-metadata">
                    <span>
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
                    </span>
                </LintSection>
                <LintSection :okay="outputsOkay" title="Outputs" collapse-id="c-outputs">
                    <span>
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
                                        <!--
                                    <font-awesome-icon icon="cog"
                                                        v-b-tooltip.hover
                                                        title="Unmark this output as a workflow output."
                                                        @click="extractWorkflowInput(output)"
                                    />
                                    -->
                                    </span>
                                </li>
                            </ul>
                        </div>
                    </span>
                </LintSection>
                <LintSection :okay="annotationOkay" title="Metadata - Annotation" collapse-id="c-annotation">
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
                </LintSection>
                <LintSection :okay="licenseOkay" title="Metadata - License" collapse-id="c-license">
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
                </LintSection>
                <LintSection :okay="creatorOkay" title="Metadata - Creator" collapse-id="c-creator">
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
                </LintSection>
                <!--
                Had tried to make this a middle panel thing, but it breaks the workflow
                to modify it while the canvas is not displayed.
                <b-button
                    id="done"
                    type="submit"
                    variant="primary"
                    v-b-tooltip.bottom.hover
                    title="Return to the workflow editor"
                    @click="doReturn"
                >
                    <i class="icon fa fa-edit" /> Return to Editor
                </b-button>
                -->
            </b-col>
        </b-row>
    </b-container>
</template>

<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import { LegacyParameters } from "components/Workflow/Editor/modules/utilities";
import LintSection from "./LintSection";
import { getDisconnectedInputs, getInputsMissingMetadata, getWorkflowOutputs } from "./modules/utilities";

Vue.use(BootstrapVue);

import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCog, faPencilAlt } from "@fortawesome/free-solid-svg-icons";

library.add(faCog);
library.add(faPencilAlt);

export default {
    components: {
        LintSection,
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

<style scoped>
.disconnected-input-name {
    padding-left: 5px;
    display: block;
}
.unlabeled-output-name {
    padding-left: 5px;
    display: block;
}
.input-missing-metadata-summary {
    display: block;
    padding-left: 5px;
}
.scrolls {
    cursor: pointer;
}
</style>

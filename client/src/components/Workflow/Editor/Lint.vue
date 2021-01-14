<template>
    <b-card header-tag="header" body-class="p-0">
        <template #header>
            <div class="mb-0 font-weight-bold">Validation Results</div>
            <div v-if="showFixAll">
                <a href="#" @click="fixAll">Attempt to fix any issue that can be automatically fixed.</a>
            </div>
        </template>
        <b-card-body>
            <LintSection
                success-message="Workflow parameters are using formal inputs."
                warning-message="This workflow uses implicit workflow parameters. They should be replaced with
                formal workflow inputs:"
                :warning-items="warningImplicitParameters"
                @onMouseOver="highlight"
                @onMouseLeave="unhighlight"
                @onClick="scrollTo"
            />
            <LintSection
                success-message="All non-optional inputs to workflow steps are connected to formal workflow inputs."
                warning-message="Some non-optional inputs are not connected to formal workflow inputs:"
                :warning-items="warningDisconnectedInputs"
                @onMouseOver="highlight"
                @onMouseLeave="unhighlight"
                @onClick="scrollTo"
            />
            <LintSection
                success-message="All workflow inputs have labels and annotations."
                warning-message="Some workflow inputs are missing labels and/or annotations:"
                :warning-items="warningMissingMetadata"
                @onMouseOver="highlight"
                @onMouseLeave="unhighlight"
                @onClick="scrollTo"
            />
            <LintSection
                success-message="This workflow has outputs and they all have valid labels."
                warning-message="The following workflow outputs have no labels, they should be assigned a useful label or
                    unchecked in the workflow editor to mark them as no longer being a workflow output:"
                :warning-items="warningUnlabeledOutputs"
                @onMouseOver="highlight"
                @onMouseLeave="unhighlight"
                @onClick="scrollTo"
            />
            <span>
                <div v-if="checkAnnotation">
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
                <div v-if="checkLicense">
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
                <div v-if="checkCreator">
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
import { ImplicitParameters } from "components/Workflow/Editor/modules/parameters";
import LintSection from "components/Workflow/Editor/LintSection";
import { getDisconnectedInputs, getInputsMissingMetadata, getWorkflowOutputs } from "./modules/linting";

Vue.use(BootstrapVue);

import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCheck, faExclamationTriangle, faPencilAlt } from "@fortawesome/free-solid-svg-icons";

library.add(faPencilAlt);
library.add(faCheck);
library.add(faExclamationTriangle);

export default {
    components: {
        FontAwesomeIcon,
        LintSection,
    },
    props: {
        implicitParameters: {
            type: ImplicitParameters,
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
                "Formal inputs make tracking workflow provenance, usage within subworkflows, and executing the workflow via the API all more robust.",
            forceRefresh: 0,
        };
    },
    methods: {
        refresh() {
            // I tried to make these purely reactive but I guess it is not surprising that the
            // entirity of the nodes object and children aren't all purely reactive.
            // https://logaretm.com/blog/2019-10-11-forcing-recomputation-of-computed-properties/
            this.forceRefresh += 1;
        },
        onAttributes() {
            this.$emit("onAttributes");
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
        fixAll() {
            const actions = [];
            if (!this.checkImplicitParameters) {
                const implicitParametersArray = this.implicitParameters ? this.implicitParameters.parameters : [];
                for (const implicitParameter of implicitParametersArray) {
                    if (implicitParameter.canExtract) {
                        actions.push({
                            action_type: "extract_implicit_parameter",
                            name: implicitParameter.name,
                        });
                    }
                }
            }
            if (!this.checkDisconnectedInputs) {
                const disconnectedInputs = getDisconnectedInputs(this.nodes);
                for (const disconnectedInput of disconnectedInputs) {
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
            if (!this.checkUnlabeledOutputs) {
                actions.push({ action_type: "remove_unlabeled_workflow_outputs" });
            }
            this.$emit("refactor", actions);
        },
    },
    computed: {
        showFixAll() {
            // we could be even more percise here and check the inputs and such, because
            // of these extractions may not be possible.
            return !this.checkImplicitParameters || !this.checkDisconnectedInputs || !this.checkUnlabeledOutputs;
        },
        checkAnnotation() {
            return !!this.annotation;
        },
        checkLicense() {
            return !!this.license;
        },
        checkCreator() {
            if (this.creator instanceof Array) {
                return this.creator.length > 0;
            } else {
                return !!this.creator;
            }
        },
        checkImplicitParameters() {
            return this.warningImplicitParameters.length == 0;
        },
        checkDisconnectedInputs() {
            return this.warningDisconnectedInputs.length == 0;
        },
        checkUnlabeledOutputs() {
            return this.warningUnlabeledOutputs.length == 0;
        },
        warningImplicitParameters() {
            let items = [];
            if (this.implicitParameters) {
                this.implicitParameters.parameters.forEach(parameter => {
                    items.push({
                        stepId: parameter.references[0].nodeId,
                        stepLabel: parameter.references[0].toolInput.label,
                        warningLabel: parameter.name,
                    });
                });
            }
            return items;
        },
        warningDisconnectedInputs() {
            this.forceRefresh;
            const disconnectedInputs = getDisconnectedInputs(this.nodes);
            let items = [];
            if (disconnectedInputs) {
                disconnectedInputs.forEach(input => {
                    items.push({
                        stepId: input.stepId,
                        stepLabel: input.stepLabel,
                        warningLabel: input.inputLabel,
                    });
                });
            }
            return items;
        },
        warningMissingMetadata() {
            this.forceRefresh;
            const inputsMissingMetadata = getInputsMissingMetadata(this.nodes);
            let items = [];
            if (inputsMissingMetadata) {
                inputsMissingMetadata.forEach(input => {
                    let missingLabel = null;
                    if (input.missingLabel && input.missingAnnotation) {
                        missingLabel = "missing a label and annotation";
                    } else if (input.missingLabel) {
                        missingLabel = "missing a label";
                    } else {
                        missingLabel = "missing an annotation";
                    }
                    items.push({
                        stepId: input.stepId,
                        stepLabel: input.stepLabel,
                        warningLabel: missingLabel,
                    });
                });
            }
            return items;
        },
        warningUnlabeledOutputs() {
            this.forceRefresh;
            const workflowOutputs = getWorkflowOutputs(this.nodes);
            let items = [];
            if (workflowOutputs) {
                workflowOutputs.forEach(output => {
                    if (output.outputLabel == null) {
                        items.push({
                            stepId: output.stepId,
                            stepLabel: output.stepLabel,
                            warningLabel: output.outputName,
                        });
                    }
                });
            }
            return items;
        },
    },
};
</script>

<template>
    <FormCard :title="node.name" :icon="nodeIcon">
        <template v-slot:operations>
            <b-button
                v-if="isSubworkflow"
                role="button"
                title="Edit this Subworkflow. You will need to upgrade this Workflow Step afterwards."
                variant="link"
                size="sm"
                class="float-right py-0 px-1"
                v-b-tooltip.hover
                @click="onEditSubworkflow"
            >
                <span class="fa fa-pencil-alt" />
            </b-button>
            <b-button
                v-if="isSubworkflow"
                role="button"
                title="Upgrade this Workflow Step to latest Subworkflow version."
                variant="link"
                size="sm"
                class="float-right py-0 px-1"
                v-b-tooltip.hover
                @click="onUpgradeSubworkflow"
            >
                <span class="fa fa-sync" />
            </b-button>
        </template>
        <template v-slot:body>
            <FormElement
                id="__label"
                :value="node.label"
                title="Label"
                help="Add a step label."
                @input="onLabel"
                :error="errorLabel"
            />
            <FormElement
                id="__annotation"
                :value="node.annotation"
                title="Step Annotation"
                :area="true"
                help="Add an annotation or notes to this step. Annotations are available when a workflow is viewed."
                @input="onAnnotation"
            />
            <FormDisplay v-if="!isSubworkflow" :id="id" :inputs="inputs" @onChange="onChange" />
            <div v-else>
                <FormOutputLabel
                    v-for="(output, index) in outputs"
                    :key="index"
                    :name="output.name"
                    :label="getOutputLabel(output)"
                    :error="outputLabelError"
                    :show-details="true"
                    @onLabel="onOutputLabel"
                />
            </div>
        </template>
    </FormCard>
</template>

<script>
import FormDisplay from "components/Form/FormDisplay";
import FormCard from "components/Form/FormCard";
import FormElement from "components/Form/FormElement";
import FormOutputLabel from "./FormOutputLabel";
import WorkflowIcons from "components/Workflow/icons";
import { checkLabels } from "components/Workflow/Editor/modules/utilities";

export default {
    components: {
        FormDisplay,
        FormCard,
        FormElement,
        FormOutputLabel,
    },
    props: {
        datatypes: {
            type: Array,
            required: true,
        },
        getManager: {
            type: Function,
            required: true,
        },
        getNode: {
            type: Function,
            required: true,
        },
    },
    data() {
        return {
            outputLabelError: null,
        };
    },
    computed: {
        node() {
            return this.getNode();
        },
        nodeIcon() {
            return WorkflowIcons[this.node.type];
        },
        workflow() {
            return this.getManager();
        },
        id() {
            return this.node.id;
        },
        inputs() {
            return this.node.config_form.inputs;
        },
        isSubworkflow() {
            return this.node.type == "subworkflow";
        },
        errorLabel() {
            return checkLabels(this.node.id, this.node.label, this.workflow.nodes);
        },
        activeOutputs() {
            return this.node.activeOutputs;
        },
        outputs() {
            return this.node.outputs;
        },
    },
    methods: {
        getOutputLabel(output) {
            const activeOutput = this.activeOutputs.get(output.name);
            return activeOutput && activeOutput.label;
        },
        onAnnotation(newAnnotation) {
            this.$emit("onAnnotation", this.node.id, newAnnotation);
        },
        onLabel(newLabel) {
            this.$emit("onLabel", this.node.id, newLabel);
        },
        onEditSubworkflow() {
            this.$emit("onEditSubworkflow", this.node.content_id);
        },
        onUpgradeSubworkflow() {
            this.$emit("onAttemptRefactor", [
                { action_type: "upgrade_subworkflow", step: { order_index: parseInt(this.node.id) } },
            ]);
        },
        onChange(values) {
            this.$emit("onSetData", this.node.id, {
                id: this.node.id,
                type: this.node.type,
                content_id: this.node.content_id,
                inputs: values,
            });
        },
        onOutputLabel(pjaKey, outputName, newLabel) {
            if (this.node.labelOutput(outputName, newLabel)) {
                this.outputLabelError = null;
            } else {
                this.outputLabelError = `Duplicate output label '${newLabel}' will be ignored.`;
            }
        },
    },
};
</script>

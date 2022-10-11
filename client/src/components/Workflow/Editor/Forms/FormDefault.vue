<template>
    <FormCard :title="nodeName" :icon="nodeIcon">
        <template v-slot:operations>
            <b-button
                v-if="isSubworkflow"
                v-b-tooltip.hover
                role="button"
                title="Edit this Subworkflow. You will need to upgrade this Workflow Step afterwards."
                variant="link"
                size="sm"
                class="float-right py-0 px-1"
                @click="onEditSubworkflow">
                <span class="fa fa-pencil-alt" />
            </b-button>
            <b-button
                v-if="isSubworkflow"
                v-b-tooltip.hover
                role="button"
                title="Upgrade this Workflow Step to latest Subworkflow version."
                variant="link"
                size="sm"
                class="float-right py-0 px-1"
                @click="onUpgradeSubworkflow">
                <span class="fa fa-sync" />
            </b-button>
        </template>
        <template v-slot:body>
            <FormElement
                id="__label"
                :value="nodeLabel"
                title="Label"
                help="Add a step label."
                :error="errorLabel"
                @input="onLabel" />
            <FormElement
                id="__annotation"
                :value="nodeAnnotation"
                title="Step Annotation"
                :area="true"
                help="Add an annotation or notes to this step. Annotations are available when a workflow is viewed."
                @input="onAnnotation" />
            <FormDisplay :id="id" :inputs="inputs" @onChange="onChange" />
            <div v-if="isSubworkflow">
                <FormOutputLabel
                    v-for="(output, index) in nodeOutputs"
                    :key="index"
                    :name="output.name"
                    :active-outputs="nodeActiveOutputs"
                    :show-details="true" />
            </div>
        </template>
    </FormCard>
</template>

<script>
import FormDisplay from "components/Form/FormDisplay";
import FormCard from "components/Form/FormCard";
import FormElement from "components/Form/FormElement";
import FormOutputLabel from "./FormOutputLabel";
import { checkLabels } from "components/Workflow/Editor/modules/utilities";
import WorkflowIcons from "components/Workflow/icons";

export default {
    components: {
        FormDisplay,
        FormCard,
        FormElement,
        FormOutputLabel,
    },
    props: {
        nodeName: {
            type: String,
            required: true,
        },
        nodeId: {
            type: String,
            required: true,
        },
        nodeContentId: {
            type: String,
            required: true,
        },
        nodeAnnotation: {
            type: String,
            required: false,
        },
        nodeLabel: {
            type: String,
            required: true,
        },
        nodeType: {
            type: String,
            required: true,
        },
        nodeActiveOutputs: {
            type: Object,
            required: true,
        },
        nodeOutputs: {
            type: Array,
            required: true,
        },
        configForm: {
            type: Object,
            required: true,
        },
        datatypes: {
            type: Array,
            required: true,
        },
        getManager: {
            type: Function,
            required: true,
        },
    },
    computed: {
        nodeIcon() {
            return WorkflowIcons[this.nodeType];
        },
        workflow() {
            return this.getManager();
        },
        id() {
            return this.nodeId;
        },
        inputs() {
            return this.configForm.inputs;
        },
        isSubworkflow() {
            return this.nodeType == "subworkflow";
        },
        errorLabel() {
            return checkLabels(this.nodeId, this.nodeLabel, this.workflow.nodes);
        },
    },
    methods: {
        onAnnotation(newAnnotation) {
            this.$emit("onAnnotation", this.nodeId, newAnnotation);
        },
        onLabel(newLabel) {
            this.$emit("onLabel", this.nodeId, newLabel);
        },
        onEditSubworkflow() {
            this.$emit("onEditSubworkflow", this.nodeContentId);
        },
        onUpgradeSubworkflow() {
            this.$emit("onAttemptRefactor", [
                { action_type: "upgrade_subworkflow", step: { order_index: parseInt(this.nodeId) } },
            ]);
        },
        onChange(values) {
            this.$emit("onSetData", this.nodeId, {
                id: this.nodeId,
                type: this.nodeType,
                content_id: this.nodeContentId,
                inputs: values,
            });
        },
    },
};
</script>

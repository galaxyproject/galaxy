<template>
    <FormCard :title="node.name" :icon="nodeIcon">
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
                :value="node.label"
                title="Label"
                help="Add a step label."
                :error="errorLabel"
                @input="onLabel" />
            <FormElement
                id="__annotation"
                :value="node.annotation"
                title="Step Annotation"
                :area="true"
                help="Add an annotation or notes to this step. Annotations are available when a workflow is viewed."
                @input="onAnnotation" />
            <FormDisplay :id="id" :inputs="inputs" @onChange="onChange" />
            <div v-if="isSubworkflow">
                <FormOutputLabel
                    v-for="(output, index) in node.outputs"
                    :key="index"
                    :name="output.name"
                    :active-outputs="node.activeOutputs"
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
    },
    methods: {
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
    },
};
</script>

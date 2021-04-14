<template>
    <div v-if="node">
        <FormElement
            id="__label"
            :value="node.label"
            title="Label"
            help="Add a step label."
            @onChange="onLabel"
            :error="errorLabel"
        />
        <FormElement
            id="__annotation"
            :value="node.annotation"
            title="Step Annotation"
            :area="true"
            help="Add an annotation or notes to this step. Annotations are available when a workflow is viewed."
            @onChange="onAnnotation"
        />
        <Form :inputs="inputs" />
    </div>
</template>

<script>
import Form from "components/Form/Form";
import FormElement from "components/Form/FormElement";

export default {
    components: {
        Form,
        FormElement,
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
            errorLabel: null,
        };
    },
    computed: {
        node() {
            return this.getNode();
        },
        inputs() {
            return this.getNode().config_form.inputs;
        },
        workflow() {
            return this.getManager();
        },
    },
    methods: {
        onAnnotation(newAnnotation) {
            this.node.setAnnotation(newAnnotation);
        },
        onLabel(newLabel) {
            this.node.setLabel(newLabel);
            let duplicate = false;
            for (const i in this.workflow.nodes) {
                const n = this.workflow.nodes[i];
                if (n.label && n.label == newLabel && n.id != this.node.id) {
                    duplicate = true;
                    break;
                }
            }
            if (duplicate) {
                this.errorLabel = "Duplicate label. Please fix this before saving the workflow.";
            } else {
                this.errorLabel = "";
            }
        },
    },
};
</script>

<template>
    <FormCardTool
        :title="node.name"
        :id="node.config_form.id"
        :description="node.config_form.description"
        :version="node.config_form.version"
        :versions="node.config_form.versions"
        :sharable-url="node.config_form.sharable_url"
    >
        <template v-slot:body>
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
            <Form :id="id" :inputs="inputs" @onChange="onChange" />
        </template>
    </FormCardTool>
</template>

<script>
import axios from "axios";
import { getAppRoot } from "onload/loadConfig";
import Form from "components/Form/Form";
import FormCardTool from "components/Form/FormCardTool";
import FormElement from "components/Form/FormElement";

export default {
    components: {
        Form,
        FormCardTool,
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
        workflow() {
            return this.getManager();
        },
        id() {
            return this.node.id;
        },
        inputs() {
            return this.node.config_form.inputs;
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
        onEditSubworkflow() {
            this.workflow.onEditSubworkflow(this.node.content_id);
        },
        onUpgradeSubworkflow() {
            this.workflow.onAttemptRefactor([
                { action_type: "upgrade_subworkflow", step: { order_index: parseInt(this.node.id) } },
            ]);
        },
        onChange(values) {
            axios
                .post(`${getAppRoot()}api/workflows/build_module`, {
                    id: this.node.id,
                    type: this.node.type,
                    content_id: this.node.content_id,
                    inputs: values,
                })
                .then((response) => {
                    const data = response.data;
                    this.node.config_form = data.config_form;
                    this.node.tool_state = data.tool_state;
                    this.node.inputs = data.inputs ? data.inputs.slice() : [];
                    this.node.outputs = data.outputs ? data.outputs.slice() : [];
                });
        },
    },
};
</script>

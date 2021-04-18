<template>
    <FormCardTool
        :id="node.config_form.id"
        :version="node.config_form.version"
        :title="node.config_form.name"
        :description="node.config_form.description"
        :options="node.config_form"
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
            <Form
                :id="id"
                :inputs="inputs"
                :initialErrors="true"
                textEnable="Set in Advance"
                textDisable="Set at Runtime"
                @onChange="onChange"
                ref="form"
            />
            <FormSection :id="id" :getNode="getNode" :datatypes="datatypes" @onChange="onChangeSection" />
        </template>
    </FormCardTool>
</template>

<script>
import axios from "axios";
import { getAppRoot } from "onload/loadConfig";
import Form from "components/Form/Form";
import FormCardTool from "components/Form/FormCardTool";
import FormSection from "./FormSection";
import FormElement from "components/Form/FormElement";
import { checkLabels } from "components/Workflow/Editor/modules/utilities";
import Utils from "utils/utils";

export default {
    components: {
        Form,
        FormCardTool,
        FormElement,
        FormSection,
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
            mainValues: {},
            sectionValues: {},
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
            const inputs = this.node.config_form.inputs;
            Utils.deepeach(inputs, (input) => {
                if (input.type) {
                    if (["data", "data_collection"].indexOf(input.type) != -1) {
                        input.hiddenInWorkflow = true;
                        input.info = `Data input '${input.name}' (${Utils.textify(input.extensions)})`;
                        input.value = { __class__: "RuntimeValue" };
                    } else if (!input.fixed) {
                        input.connectable = true;
                        input.collapsible_value = {
                            __class__: "RuntimeValue",
                        };
                        input.is_workflow =
                            (input.options && input.options.length === 0) ||
                            ["integer", "float"].indexOf(input.type) != -1;
                    }
                }
            });
            Utils.deepeach(inputs, (input) => {
                if (input.type === "conditional") {
                    input.connectable = false;
                    input.test_param.collapsible_value = undefined;
                }
            });
            return inputs;
        },
    },
    methods: {
        onAnnotation(newAnnotation) {
            this.node.setAnnotation(newAnnotation);
        },
        onLabel(newLabel) {
            this.node.setLabel(newLabel);
            this.errorLabel = checkLabels(this.node.id, newLabel, this.workflow.nodes);
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
            this.mainValues = values;
            this.postChanges();
        },
        onChangeSection(values) {
            this.sectionValues = values;
            console.log(this.sectionValues);
            this.postChanges();
        },
        postChanges() {
            const options = this.node.config_form;
            axios
                .post(`${getAppRoot()}api/workflows/build_module`, {
                    tool_id: options.id,
                    tool_version: options.version,
                    type: "tool",
                    inputs: Object.assign({}, this.mainValues),
                })
                .then(({ data }) => {
                    this.node.config_form = data.config_form;
                    this.node.tool_state = data.tool_state;
                    this.node.inputs = data.inputs ? data.inputs.slice() : [];
                    this.node.outputs = data.outputs ? data.outputs.slice() : [];
                    const form = this.$refs["form"];
                    console.log(form);
                    form.parseUpdate(data.config_form);
                    form.parseErrors(data.config_form);
                });
        },
    },
};
</script>

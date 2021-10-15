<template>
    <div v-if="firstOutput">
        <FormElement
            :id="emailActionId"
            :value="emailActionValue"
            title="Email notification"
            type="boolean"
            help="An email notification will be sent when the job has completed."
            @input="onInput"
        />
        <FormElement
            :id="deleteActionId"
            :value="deleteActionValue"
            title="Output cleanup"
            type="boolean"
            help="Upon completion of this step, delete non-starred outputs from completed workflow steps if they are no longer required as inputs."
            @input="onInput"
        />
        <FormOutput
            v-for="(output, index) in outputs"
            :key="index"
            :outputName="output.name"
            :outputLabel="getOutputLabel(output)"
            :inputs="node.inputs"
            :datatypes="datatypes"
            :form-data="formData"
            @onInput="onInput"
            @onLabel="onLabel"
            @onDatatype="onDatatype"
        />
    </div>
</template>

<script>
import FormElement from "components/Form/FormElement";
import FormOutput from "./FormOutput";

export default {
    components: {
        FormElement,
        FormOutput,
    },
    props: {
        id: {
            type: String,
            required: true,
        },
        getNode: {
            type: Function,
            required: true,
        },
        datatypes: {
            type: Array,
            required: true,
        },
    },
    data() {
        return {
            formData: {},
        };
    },
    watch: {
        id() {
            this.setFormData();
        },
    },
    created() {
        this.setFormData();
    },
    computed: {
        node() {
            return this.getNode();
        },
        postJobActions() {
            return this.node.postJobActions;
        },
        activeOutputs() {
            return this.node.activeOutputs;
        },
        outputs() {
            return this.node.outputs;
        },
        firstOutput() {
            return this.outputs.length > 0 && this.outputs[0];
        },
        emailActionId() {
            return `pja__${this.firstOutput.name}__EmailAction`;
        },
        emailActionValue() {
            return Boolean(this.postJobActions[`EmailAction${this.firstOutput.name}`]);
        },
        deleteActionId() {
            return `pja__${this.firstOutput.name}__DeleteIntermediatesAction`;
        },
        deleteActionValue() {
            return Boolean(this.postJobActions[`DeleteIntermediatesAction${this.firstOutput.name}`]);
        },
    },
    methods: {
        setFormData() {
            const pjas = {};
            Object.values(this.postJobActions).forEach((pja) => {
                Object.entries(pja.action_arguments).forEach(([name, value]) => {
                    const key = `pja__${pja.output_name}__${pja.action_type}__${name}`;
                    pjas[key] = value;
                });
            });
            const emailPayloadKey = `${this.emailActionId()}__host`;
            this.formData[emailPayloadKey] = window.location.host;
            this.formData = pjas;
        },
        getOutputLabel(output) {
            const activeOutput = this.activeOutputs.get(output.name);
            return activeOutput && activeOutput.label;
        },
        onInput(value, identifier) {
            if (value) {
                this.formData[identifier] = value;
            } else if (identifier in this.formData) {
                delete this.formData[identifier];
            }
            this.$emit("onChange", this.formData);
        },
        onLabel(outputName, newLabel) {
            /*const oldLabel = node.labelOutput(outputName, newLabel);
            const input_id = form.data.match(`__label__${outputName}`);
            const input_element = form.element_list[input_id];
            if (oldLabel) {
                input_element.field.model.set("value", oldLabel);
                input_element.model.set(
                    "error_text",
                    `Duplicate output label '${newLabel}' will be ignored.`
                );
            } else {
                input_element.model.set("error_text", "");
            }
            form.trigger("change");*/
        },
        onDatatype(outputName, newDatatype) {
            this.$emit("onChangeOutputDatatype", outputName, newDatatype);
        },
    },
};
</script>

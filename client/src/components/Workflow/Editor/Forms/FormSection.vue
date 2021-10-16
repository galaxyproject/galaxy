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
            :output-label-error="outputLabelError"
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
            outputLabelError: null,
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
            const emailPayloadKey = `${this.emailActionId}__host`;
            pjas[emailPayloadKey] = window.location.host;
            this.formData = pjas;
        },
        getOutputLabel(output) {
            const activeOutput = this.activeOutputs.get(output.name);
            return activeOutput && activeOutput.label;
        },
        onInput(value, identifier) {
            let changed = false;
            const exists = identifier in this.formData;
            if (value) {
                const oldValue = this.formData[identifier];
                if (value != oldValue) {
                    this.formData[identifier] = value;
                    changed = true;
                }
            } else if (exists) {
                changed = true;
                delete this.formData[identifier];
            }
            if (changed) {
                this.$emit("onChange", this.formData);
            }
        },
        onLabel(pjaKey, outputName, newLabel) {
            const oldLabel = this.node.labelOutput(outputName, newLabel);
            if (oldLabel) {
                this.outputLabelError = `Duplicate output label '${newLabel}' will be ignored.`;
            } else {
                this.outputLabelError = null;
            }
            this.onInput(newLabel, pjaKey);
        },
        onDatatype(pjaKey, outputName, newDatatype) {
            this.onInput(newDatatype, pjaKey);
        },
    },
};
</script>

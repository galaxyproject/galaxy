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
            return Boolean(this.formData[this.emailActionId]);
        },
        deleteActionId() {
            return `pja__${this.firstOutput.name}__DeleteIntermediatesAction`;
        },
        deleteActionValue() {
            return Boolean(this.formData[this.deleteActionId]);
        },
    },
    methods: {
        setFormData() {
            const pjas = {};
            Object.values(this.postJobActions).forEach((pja) => {
                if (Object.keys(pja.action_arguments).length > 0) {
                    Object.entries(pja.action_arguments).forEach(([name, value]) => {
                        const key = `pja__${pja.output_name}__${pja.action_type}__${name}`;
                        pjas[key] = value;
                    });
                } else {
                    const key = `pja__${pja.output_name}__${pja.action_type}`;
                    pjas[key] = true;
                }
            });
            this.setEmailAction(pjas);
            this.formData = pjas;
            console.debug("FormSection - Setting new data.", this.postJobActions, pjas);
            this.$emit("onChange", this.formData);
        },
        setEmailAction(pjas) {
            const emailPayloadKey = `${this.emailActionId}__host`;
            if (pjas[this.emailActionId]) {
                pjas[emailPayloadKey] = window.location.host;
            } else if (emailPayloadKey in pjas) {
                delete pjas[emailPayloadKey];
            }
        },
        getOutputLabel(output) {
            const activeOutput = this.activeOutputs.get(output.name);
            return activeOutput && activeOutput.label;
        },
        onInput(value, pjaKey) {
            let changed = false;
            const exists = pjaKey in this.formData;
            if (![null, undefined, "", false].includes(value)) {
                const oldValue = this.formData[pjaKey];
                if (value !== oldValue) {
                    this.formData[pjaKey] = value;
                    changed = true;
                }
            } else if (exists) {
                changed = true;
                delete this.formData[pjaKey];
            }
            this.setEmailAction(this.formData);
            if (changed) {
                this.formData = Object.assign({}, this.formData);
                this.$emit("onChange", this.formData);
            }
        },
        onLabel(pjaKey, outputName, newLabel) {
            if (this.node.labelOutput(outputName, newLabel)) {
                this.outputLabelError = null;
                this.onInput(newLabel, pjaKey);
            } else {
                this.outputLabelError = `Duplicate output label '${newLabel}' will be ignored.`;
            }
        },
        onDatatype(pjaKey, outputName, newDatatype) {
            this.onInput(newDatatype, pjaKey);
        },
    },
};
</script>

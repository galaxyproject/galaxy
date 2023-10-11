<template>
    <div v-if="firstOutput">
        <FormElement
            :id="emailActionKey"
            :value="emailActionValue"
            title="Email notification"
            type="boolean"
            help="An email notification will be sent when the job has completed."
            @input="onInput" />
        <FormElement
            :id="deleteActionKey"
            :value="deleteActionValue"
            title="Output cleanup"
            type="boolean"
            help="Upon completion of this step, delete unchecked outputs from completed workflow steps if they are no longer required as inputs."
            @input="onInput" />
        <FormOutput
            v-for="(output, index) in outputs"
            :key="index"
            :output-name="output.name"
            :step="step"
            :inputs="nodeInputs"
            :datatypes="datatypes"
            :form-data="formData"
            @onInput="onInput"
            @onDatatype="onDatatype" />
    </div>
</template>

<script>
import FormElement from "@/components/Form/FormElement";
import FormOutput from "@/components/Workflow/Editor/Forms/FormOutput";

export default {
    components: {
        FormElement,
        FormOutput,
    },
    props: {
        id: {
            type: Number,
            required: true,
        },
        nodeInputs: {
            type: Array,
            required: true,
        },
        nodeOutputs: {
            type: Array,
            required: true,
        },
        step: {
            // type Step from @/stores/workflowStepStore
            type: Object,
            required: true,
        },
        datatypes: {
            type: Array,
            required: true,
        },
        postJobActions: {
            type: Object,
            required: true,
        },
    },
    data() {
        return {
            formData: {},
        };
    },
    computed: {
        outputs() {
            return this.nodeOutputs;
        },
        firstOutput() {
            return this.outputs.length > 0 && this.outputs[0];
        },
        emailActionKey() {
            return `pja__${this.firstOutput.name}__EmailAction`;
        },
        emailPayloadKey() {
            return `${this.emailActionKey}__host`;
        },
        emailActionValue() {
            return Boolean(this.formData[this.emailActionKey]);
        },
        deleteActionKey() {
            return `pja__${this.firstOutput.name}__DeleteIntermediatesAction`;
        },
        deleteActionValue() {
            return Boolean(this.formData[this.deleteActionKey]);
        },
    },
    watch: {
        formData() {
            // The formData shape is kind of unfortunate, but it is what we have now.
            // This should be a properly nested object whose values should be retrieved and set via a store
            const postJobActions = {};
            Object.entries(this.formData).forEach(([key, value]) => {
                const [pja, outputName, actionType, name] = key.split("__", 4);
                if (pja == "pja") {
                    const pjaKey = `${actionType}${outputName}`;
                    if (!postJobActions[pjaKey]) {
                        postJobActions[pjaKey] = {
                            action_type: actionType,
                            output_name: outputName,
                            action_arguments: {},
                        };
                    }
                    if (name) {
                        if (name == "output_name") {
                            postJobActions[pjaKey]["output_name"] = value;
                        } else {
                            postJobActions[pjaKey]["action_arguments"][name] = value;
                        }
                    }
                }
            });
            this.$emit("onChange", postJobActions);
        },
    },
    created() {
        this.setFormData();
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
            if (pjas[this.emailPayloadKey]) {
                pjas[this.emailActionKey] = true;
            }
            this.formData = pjas;
        },
        setEmailAction(pjas) {
            if (pjas[this.emailActionKey]) {
                pjas[this.emailPayloadKey] = window.location.host;
            } else if (this.emailPayloadKey in pjas) {
                delete pjas[this.emailPayloadKey];
            }
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
            }
        },
        onDatatype(pjaKey, outputName, newDatatype) {
            this.onInput(newDatatype, pjaKey);
        },
    },
};
</script>

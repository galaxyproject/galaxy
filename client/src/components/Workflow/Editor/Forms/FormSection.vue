<template>
    <div v-if="firstOutput">
        <GAlert v-if="hasLegacyEmailAction" variant="warning" data-test-id="removed-email-action">
            Step email notifications have been removed. This action no longer sends email. Use the notification controls
            on the workflow run form instead.
            <GButton size="small" class="mt-2" @click="removeEmailActions">Remove obsolete email action</GButton>
        </GAlert>
        <FormElement
            v-if="supportsJobBasedActions"
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
import GAlert from "@/components/BaseComponents/GAlert.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import FormElement from "@/components/Form/FormElement.vue";
import FormOutput from "@/components/Workflow/Editor/Forms/FormOutput.vue";

export default {
    components: {
        GAlert,
        GButton,
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
        supportsJobBasedActions: {
            type: Boolean,
            default: true,
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
        hasLegacyEmailAction() {
            return Object.keys(this.formData).some((key) => key.split("__")[2] === "EmailAction");
        },
        deleteActionKey() {
            return `pja__${this.firstOutput.name}__DeleteIntermediatesAction`;
        },
        deleteActionValue() {
            return Boolean(this.formData[this.deleteActionKey]);
        },
    },
    created() {
        this.setFormData();
    },
    methods: {
        postPostJobActions() {
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
            this.formData = pjas;
        },
        removeEmailActions() {
            this.formData = Object.fromEntries(
                Object.entries(this.formData).filter(([key]) => key.split("__")[2] !== "EmailAction"),
            );
            this.postPostJobActions();
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
            if (changed) {
                this.formData = Object.assign({}, this.formData);
                this.postPostJobActions();
            }
        },
        onDatatype(pjaKey, outputName, newDatatype) {
            this.onInput(newDatatype, pjaKey);
        },
    },
};
</script>

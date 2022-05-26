<template>
    <div :step-label="model.step_label">
        <FormCard :title="model.fixed_title" :icon="icon" :collapsible="true" :expanded.sync="expanded">
            <template v-slot:body>
                <FormDisplay
                    v-if="hasInputs"
                    :inputs="inputs"
                    :replace-params="replaceParams"
                    :validation-scroll-to="validationScrollTo"
                    @onChange="onChange"
                    @onValidation="onValidation" />
                <div v-else class="py-2">No options available.</div>
            </template>
        </FormCard>
    </div>
</template>

<script>
import { visitInputs } from "components/Form/utilities";
import WorkflowIcons from "components/Workflow/icons";
import FormDisplay from "components/Form/FormDisplay";
import FormCard from "components/Form/FormCard";

export default {
    components: {
        FormDisplay,
        FormCard,
    },
    props: {
        model: {
            type: Object,
            required: true,
        },
        wpData: {
            type: Object,
            default: null,
        },
        validationScrollTo: {
            type: Array,
            required: true,
        },
    },
    data() {
        return {
            expanded: this.model.expanded,
            replaceParams: {},
        };
    },
    computed: {
        icon() {
            return WorkflowIcons[this.model.step_type];
        },
        isSimpleInput() {
            return (
                this.model.step_type.startsWith("data_input") ||
                this.model.step_type.startsWith("data_collection_input")
            );
        },
        inputs() {
            this.model.inputs.forEach((input) => {
                input.flavor = "module";
                input.hide_label = this.isSimpleInput;
            });
            if (this.model.inputs && this.model.inputs.length > 0) {
                return this.model.inputs;
            }
            return [];
        },
        hasInputs() {
            return this.inputs.length > 0;
        },
    },
    watch: {
        validationScrollTo() {
            if (this.validationScrollTo.length > 0) {
                this.expanded = true;
            }
        },
        wpData() {
            this.onReplaceParams();
        },
    },
    methods: {
        onChange(data) {
            this.$emit("onChange", this.model.index, data);
        },
        onReplaceParams() {
            const params = {};
            visitInputs(this.model.inputs, (input, name) => {
                params[name] = input;
            });
            this.replaceParams = {};
            _.each(params, (input, name) => {
                if (input.wp_linked) {
                    let newValue = input.value;
                    const re = /\$\{(.+?)\}/g;
                    let match;
                    while ((match = re.exec(input.value))) {
                        const wpValue = this.wpData[match[1]];
                        if (wpValue) {
                            newValue = newValue.split(match[0]).join(wpValue);
                        }
                    }
                    if (newValue !== undefined) {
                        this.replaceParams[name] = newValue;
                    }
                }
            });
        },
        onValidation(validation) {
            this.$emit("onValidation", this.model.index, validation);
        },
    },
};
</script>

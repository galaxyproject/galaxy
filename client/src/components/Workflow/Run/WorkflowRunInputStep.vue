<template>
    <div :step-label="model.step_label">
        <FormCard :title="model.fixed_title" :icon="icon" :collapsible="true" :expanded.sync="expanded">
            <template v-slot:body>
                <FormDisplay
                    v-if="hasInputs"
                    :inputs="inputs"
                    :validation-scroll-to="validationScrollTo"
                    @onChange="onChange"
                    @onValidation="onValidation" />
                <div v-else class="py-2">No options available.</div>
            </template>
        </FormCard>
    </div>
</template>

<script>
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
        validationScrollTo: {
            type: Array,
            required: true,
        },
    },
    data() {
        return {
            expanded: this.model.expanded,
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
    },
    methods: {
        onChange(data) {
            console.log("emitting default change", data);
            this.$emit("onChange", this.model.index, data);
        },
        onValidation(validation) {
            this.$emit("onValidation", this.model.index, validation);
        },
    },
};
</script>

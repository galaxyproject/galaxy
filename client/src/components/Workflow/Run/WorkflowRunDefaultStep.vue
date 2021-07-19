<template>
    <div>
        <FormCard :title="model.fixed_title" :icon="icon" :collapsible="true" :initial-collapse="false">
            <template v-slot:body>
                <FormDisplay
                    :inputs="inputs"
                    :validation-scroll-to="validationScrollTo"
                    @onChange="onChange"
                    @onValidation="onValidation"
                />
            </template>
        </FormCard>
    </div>
</template>

<script>
import { getGalaxyInstance } from "app";
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
        stepScrollTo: {
            type: Object,
            required: true,
        },
    },
    data() {
        return {
            validationScrollTo: [],
        };
    },
    watch: {
        stepScrollTo() {
            if (this.stepScrollTo && this.stepScrollTo.stepId == this.model.index) {
                this.validationScrollTo = this.stepScrollTo.validation;
            }
        },
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
            } else {
                return [
                    {
                        type: "hidden",
                        name: "No options available.",
                        ignore: null,
                    },
                ];
            }
        },
    },
    methods: {
        onChange(data) {
            this.$emit("onChange", this.model.index, data);
        },
        onValidation(validation) {
            this.$emit("onValidation", this.model.index, validation);
        },
    },
};
</script>

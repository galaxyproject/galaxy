<template>
    <div>
        <FormCard title="model.label">
            <template v-slot:body>
                <Form :inputs="inputs" />
            </template>
        </FormCard>
    </div>
</template>

<script>
import { getGalaxyInstance } from "app";
import Form from "components/Form/Form";
import FormCard from "components/Form/FormCard";

export default {
    components: {
        Form,
        FormCard,
    },
    props: {
        model: {
            type: Object,
            required: true,
        },
    },
    data() {
        return {};
    },
    created() {
        console.log(this.model);
    },
    computed: {
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
    methods: {},
};
</script>

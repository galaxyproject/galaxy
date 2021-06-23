<template>
    <div>
        <FormCard :title="title" icon="fa-wrench" :collapsible="true">
            <template v-slot:body>
                <FormMessage :message="errorText" variant="danger" :persistent="true" />
                <Form
                    :inputs="model.inputs"
                    :form-config="formConfig"
                    :replaceParams="replaceParams"
                    :replaceData="replaceData"
                    @onChange="onChange"
                />
            </template>
        </FormCard>
    </div>
</template>

<script>
import Form from "components/Form/Form";
import FormMessage from "components/Form/FormMessage";
import FormCard from "components/Form/FormCard";
import { getTool } from "./services";

export default {
    components: {
        Form,
        FormCard,
        FormMessage,
    },
    props: {
        model: {
            type: Object,
            required: true,
        },
        replaceParams: {
            type: Object,
            default: null,
        },
        replaceData: {
            type: Object,
            default: null,
        },
    },
    data() {
        return {
            formConfig: {},
            errorText: null,
        };
    },
    computed: {
        title() {
            return `${this.model.name} ${this.model.description} (Galaxy Version ${this.model.version})`;
        },
    },
    methods: {
        onChange(data) {
            getTool(this.model.id, this.model.version, data).then(
                (formConfig) => {
                    this.formConfig = formConfig;
                },
                (errorText) => {
                    this.errorText = errorText;
                }
            );
            this.$emit("onChange", this.model.index, data);
        },
    },
};
</script>

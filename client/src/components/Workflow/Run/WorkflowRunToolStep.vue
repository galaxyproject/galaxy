<template>
    <div>
        <FormCard :title="title" icon="fa-wrench" :collapsible="false">
            <template v-slot:body>
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
import FormCard from "components/Form/FormCard";
import { getTool } from "./services";

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
                (response) => {
                    //Galaxy.emit.debug("tool-form-composite::postchange()", "Refresh request failed.", response);
                    //process.reject();
                }
            );
            this.$emit("onChange", this.model.index, data);
        },
    },
};
</script>

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
import FormData from "mvc/form/form-data";
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
        wpData: {
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
            formData: {},
            replaceParams: {},
            errorText: null,
        };
    },
    watch: {
        wpData() {
            this.onReplaceParams();
        },
    },
    computed: {
        title() {
            return `${this.model.name} ${this.model.description} (Galaxy Version ${this.model.version})`;
        },
    },
    methods: {
        onReplaceParams() {
            const params = {};
            FormData.visitInputs(this.model.inputs, (input, name) => {
                params[name] = input;
            });
            const values = this.formData;
            this.replaceParams = {};
            _.each(params, (input, name) => {
                if (input.wp_linked) {
                    let new_value;
                    if (input.wp_linked) {
                        new_value = input.value;
                        var re = /\$\{(.+?)\}/g;
                        var match;
                        while ((match = re.exec(input.value))) {
                            var wp_value = this.wpData[match[1]];
                            if (wp_value) {
                                new_value = new_value.split(match[0]).join(wp_value);
                            }
                        }
                    }
                    if (new_value !== undefined) {
                        this.replaceParams[name] = new_value;
                    }
                }
            });
            console.log(this.replaceParams);
        },
        onChange(data) {
            getTool(this.model.id, this.model.version, data).then(
                (formConfig) => {
                    this.formConfig = formConfig;
                },
                (errorText) => {
                    this.errorText = errorText;
                }
            );
            this.formData = data;
            this.$emit("onChange", this.model.index, data);
        },
    },
};
</script>

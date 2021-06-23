<template>
    <div>
        <FormCard :title="title" icon="fa-wrench" :collapsible="true">
            <template v-slot:body>
                <FormMessage :message="errorText" variant="danger" :persistent="true" />
                <Form
                    :inputs="model.inputs"
                    :form-config="formConfig"
                    :replace-params="replaceParams"
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
import { visitInputs } from "components/Form/utilities";
import { isDataStep } from "components/Workflow/Run/model";
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
        stepData: {
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
        stepData() {
            this.onReplaceParams();
        },
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
            visitInputs(this.model.inputs, (input, name) => {
                params[name] = input;
            });
            const values = this.formData;
            this.replaceParams = {};
            _.each(params, (input, name) => {
                if (input.wp_linked || input.step_linked) {
                    let newValue;
                    if (input.step_linked) {
                        newValue = { values: [] };
                        _.each(input.step_linked, (source_step) => {
                            if (isDataStep(source_step)) {
                                var value = this.stepData[source_step.index].input;
                                if (value) {
                                    _.each(value.values, (v) => {
                                        newValue.values.push(v);
                                    });
                                }
                            }
                        });
                        if (!input.multiple && newValue.values.length > 0) {
                            newValue = {
                                values: [newValue.values[0]],
                            };
                        }
                    }
                    if (input.wp_linked) {
                        newValue = input.value;
                        var re = /\$\{(.+?)\}/g;
                        var match;
                        while ((match = re.exec(input.value))) {
                            var wp_value = this.wpData[match[1]];
                            if (wp_value) {
                                newValue = newValue.split(match[0]).join(wp_value);
                            }
                        }
                    }
                    if (newValue !== undefined) {
                        this.replaceParams[name] = newValue;
                    }
                }
            });
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

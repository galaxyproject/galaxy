<template>
    <div>
        <div v-for="input, index) in inputs" :key="index">
            <div v-if="input.type == 'repeat'">
                <p class="font-weight-bold mb-2">{{ input.title }}</p>
                <FormCard v-for="(cache, cacheId) in input.cache"
                    :key="cacheId"
                    :title="repeatTitle(cacheId, input.title)"
                >
                    <template v-slot:operations>
                        <b-button
                            role="button"
                            variant="link"
                            size="sm"
                            class="float-right"
                            v-b-tooltip.hover.bottom
                        >
                            <font-awesome-icon icon="trash-alt" />
                        </b-button>
                    </template>
                    <template v-slot:body>
                        <FormNode 
                            :inputs="cache"
                        />
                    </template>
                </FormCard>
                <b-button>
                    <font-awesome-icon icon="plus" class="mr-1" />
                    <span>Insert {{ input.title }}</span>
                </b-button>
            </div>
            <FormElement
                v-else
                :id="input.name"
                :title="input.label"
                :value="input.value"
                :help="input.help"
                :area="input.area"
                :type="input.type"
            />
        </div>
    </div>
</template>

<script>
import { visitInputs } from "components/Form/utilities";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faPlus, faTrashAlt } from "@fortawesome/free-solid-svg-icons";
import FormCard from "components/Form/FormCard";
import FormElement from "components/Form/FormElement";

library.add(faPlus, faTrashAlt);

export default {
    name: "FormNode",
    components: {
        FontAwesomeIcon,
        FormCard,
        FormElement,
    },
    props: {
        id: {
            type: String,
            default: null,
        },
        inputs: {
            type: Array,
            required: true,
        },
        errors: {
            type: Object,
            default: null,
        },
        sustainRepeats: {
            type: Boolean,
            default: false,
        },
        sustainConditionals: {
            type: Boolean,
            default: false,
        },
        textEnable: {
            type: String,
            default: null,
        },
        textDisable: {
            type: String,
            default: null,
        },
        validationScrollTo: {
            type: Array,
            default: null,
        },
        replaceParams: {
            type: Object,
            default: null,
        },
    },
    data() {
        return {
            formData: {},
        };
    },
    watch: {
        id() {
            //this.onRender();
        },
        validationScrollTo() {
            //this.onHighlight(this.validationScrollTo);
        },
        validation() {
            //this.onHighlight(this.validation, true);
            //this.$emit("onValidation", this.validation);
        },
        inputs() {
            /*this.$nextTick(() => {
                this.form.update(this.inputs);
            });*/
        },
        errors() {
            /*this.$nextTick(() => {
                this.form.errors(this.errors);
            });*/
        },
        replaceParams() {
            //this.onReplaceParams();
        },
    },
    created() {
        console.log(this.inputs);
    },
    computed: {
        validation() {
            /*let batch_n = -1;
            let batch_src = null;
            for (const job_input_id in this.formData) {
                const input_value = this.formData[job_input_id];
                const input_id = this.form.data.match(job_input_id);
                const input_field = this.form.field_list[input_id];
                const input_def = this.form.input_list[input_id];
                if (!input_id || !input_def || !input_field || input_def.step_linked) {
                    continue;
                }
                if (
                    input_value &&
                    Array.isArray(input_value.values) &&
                    input_value.values.length == 0 &&
                    !input_def.optional
                ) {
                    return [job_input_id, "Please provide data for this input."];
                }
                if (input_value == null && !input_def.optional && input_def.type != "hidden") {
                    return [job_input_id, "Please provide a value for this option."];
                }
                if (input_def.wp_linked && input_def.text_value == input_value) {
                    return [job_input_id, "Please provide a value for this workflow parameter."];
                }
                if (input_field.validate) {
                    const message = input_field.validate();
                    if (message) {
                        return [job_input_id, message];
                    }
                }
                if (input_value && input_value.batch) {
                    const n = input_value.values.length;
                    const src = n > 0 && input_value.values[0] && input_value.values[0].src;
                    if (src) {
                        if (batch_src === null) {
                            batch_src = src;
                        } else if (batch_src !== src) {
                            return [
                                job_input_id,
                                "Please select either dataset or dataset list fields for all batch mode fields.",
                            ];
                        }
                    }
                    if (batch_n === -1) {
                        batch_n = n;
                    } else if (batch_n !== n) {
                        return [
                            job_input_id,
                            `Please make sure that you select the same number of inputs for all batch mode fields. This field contains <b>${n}</b> selection(s) while a previous field contains <b>${batch_n}</b>.`,
                        ];
                    }
                }
            }*/
            return null;
        },
    },
    methods: {
        repeatTitle(index, title) {
            return `${index + 1}: ${title}`;
        },
        onReplaceParams() {
            /*if (this.replaceParams) {
                this.params = {};
                visitInputs(this.inputs, (input, name) => {
                    this.params[name] = input;
                });
                _.each(this.params, (input, name) => {
                    const newValue = this.replaceParams[name];
                    if (newValue) {
                        const field = this.form.field_list[this.form.data.match(name)];
                        field.value(newValue);
                    }
                });
                this.form.trigger("change");
            }*/
        },
        onChange(refreshRequest) {
            //this.formData = this.form.data.create();
            //this.$emit("onChange", this.formData, refreshRequest);
        },
        onRender() {
            /*this.$nextTick(() => {
                const el = this.$refs["form"];
                this.form = new Form({
                    el,
                    inputs: this.inputs,
                    text_enable: this.textEnable,
                    text_disable: this.textDisable,
                    sustain_repeats: this.sustainRepeats,
                    sustain_conditionals: this.sustainConditionals,
                    onchange: (refreshRequest) => {
                        this.onChange(refreshRequest);
                    },
                });
                this.onChange();
            });*/
        },
        onHighlight(validation, silent = false) {
            /*this.form.trigger("reset");
            if (validation && validation.length == 2) {
                const input_id = this.form.data.match(validation[0]);
                this.form.highlight(input_id, validation[1], silent);
            }*/
        },
    },
};
</script>

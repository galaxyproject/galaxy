<template>
    <div>
        <div v-for="(input, index) in formInputs" :key="index">
            <div v-if="input.type == 'repeat'">
                <p class="font-weight-bold mb-2">{{ input.title }}</p>
                <FormCard
                    v-for="(cache, cacheId) in input.cache"
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
                            @click="repeatDelete(input, cacheId)"
                        >
                            <font-awesome-icon icon="trash-alt" />
                        </b-button>
                    </template>
                    <template v-slot:body>
                        <FormNode
                            :inputs="cache"
                            :prefix="getRepeatPrefix(input.name, cacheId)"
                            :add-parameters="addParameters"
                            :remove-parameters="removeParameters"
                            :update-parameters="updateParameters"
                        />
                    </template>
                </FormCard>
                <b-button @click="repeatInsert(input)">
                    <font-awesome-icon icon="plus" class="mr-1" />
                    <span>Insert {{ input.title }}</span>
                </b-button>
            </div>
            <div v-else-if="input.type == 'section'">
                <FormCard :title="input.title || input.name" :expanded.sync="input.expanded" :collapsible="true">
                    <template v-slot:body>
                        <FormNode
                            :inputs="input.inputs"
                            :prefix="getPrefix(input.name)"
                            :add-parameters="addParameters"
                            :remove-parameters="removeParameters"
                            :update-parameters="updateParameters"
                        />
                    </template>
                </FormCard>
            </div>
            <FormElement
                v-else
                v-bind="input"
                :id="getPrefix(input.name)"
                :title="input.label"
                :help="input.help"
                :backbonejs="true"
                @input="addParameters"
            />
        </div>
    </div>
</template>

<script>
import Vue from "vue";
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
        inputs: {
            type: Array,
            required: true,
        },
        prefix: {
            type: String,
            default: "",
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
        errors: {
            type: Object,
            default: null,
        },
        addParameters: {
            type: Function,
            required: true,
        },
        removeParameters: {
            type: Function,
            required: true,
        },
        updateParameters: {
            type: Function,
            required: true,
        },
    },
    data() {
        return {
            formData: {},
            formInputs: this.inputs.slice(),
        };
    },
    watch: {
        inputs() {
            this.formInputs = this.inputs.slice();
        },
        validationScrollTo() {
            //this.onHighlight(this.validationScrollTo);
        },
        validation() {
            //this.onHighlight(this.validation, true);
            //this.$emit("onValidation", this.validation);
        },
        errors() {
            /*this.$nextTick(() => {
                if (this.initialErrors) {
                    this.form.errors(this.errors);
                }
            });*/
        },
    },
    methods: {
        getRepeatPrefix(name, index) {
            if (this.prefix) {
                return `${this.prefix}|${name}_${index}`;
            } else {
                return `${name}_${index}`;
            }
        },
        getPrefix(name) {
            if (this.prefix) {
                return `${this.prefix}|${name}`;
            } else {
                return name;
            }
        },
        repeatTitle(index, title) {
            return `${parseInt(index) + 1}: ${title}`;
        },
        repeatInsert(input) {
            const newInputs = JSON.parse(JSON.stringify(input.inputs));
            input.cache = input.cache || [];
            input.cache.push(newInputs);
            this.formInputs = this.formInputs.slice();
            this.updateParameters();
        },
        repeatDelete(input, cacheId) {
            const prefix = this.getPrefix(input.name);
            this.removeParameters(prefix, cacheId);
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

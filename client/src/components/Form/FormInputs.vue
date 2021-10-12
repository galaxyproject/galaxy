<template>
    <div>
        <div v-for="(input, index) in inputs" :key="index">
            <div v-if="input.type == 'conditional'">
                <FormElement
                    v-model="input.test_param.value"
                    :id="conditionalPrefix(input, input.test_param.name)"
                    :title="input.test_param.label"
                    :type="input.test_param.type"
                    :help="input.test_param.help"
                    :refreshOnChange="false"
                    :attributes="input.test_param"
                    :backbonejs="true"
                    @change="onChange"
                />
                <FormNode
                    v-for="(caseDetails, caseId) in input.cases"
                    v-if="conditionalMatch(input, caseId)"
                    :key="caseId"
                    :inputs="caseDetails.inputs"
                    :prefix="getPrefix(input.name)"
                    :onChange="onChange"
                    :onChangeForm="onChangeForm"
                />
            </div>
            <div v-else-if="input.type == 'repeat'">
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
                            :prefix="getPrefix(input.name, cacheId)"
                            :onChange="onChange"
                            :onChangeForm="onChangeForm"
                        />
                    </template>
                </FormCard>
                <b-button @click="repeatInsert(input)">
                    <font-awesome-icon icon="plus" class="mr-1" />
                    <span>Insert {{ input.title || "Repeat" }}</span>
                </b-button>
            </div>
            <div v-else-if="input.type == 'section'">
                <FormCard :title="input.title || input.name" :expanded.sync="input.expanded" :collapsible="true">
                    <template v-slot:body>
                        <FormNode
                            :inputs="input.inputs"
                            :prefix="getPrefix(input.name)"
                            :onChange="onChange"
                            :onChangeForm="onChangeForm"
                        />
                    </template>
                </FormCard>
            </div>
            <FormElement
                v-else
                v-model="input.value"
                :id="getPrefix(input.name)"
                :title="input.label"
                :type="input.type"
                :error="input.error"
                :help="input.help"
                :refreshOnChange="input.refresh_on_change"
                :attributes="input.attributes || input"
                :backbonejs="true"
                @change="onChange"
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
import { matchCase } from "components/Form/utilities";

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
            default: null,
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
        onChange: {
            type: Function,
            required: true,
        },
        onChangeForm: {
            type: Function,
            required: true,
        },
    },
    methods: {
        getPrefix(name, index) {
            if (index) {
                name = `${name}_${index}`;
            }
            if (this.prefix) {
                return `${this.prefix}|${name}`;
            } else {
                return name;
            }
        },
        conditionalPrefix(input, name) {
            return this.getPrefix(`${input.name}|${name}`);
        },
        conditionalMatch(input, caseId) {
            return matchCase(input, input.test_param.value) == caseId;
        },
        repeatTitle(index, title) {
            return `${parseInt(index) + 1}: ${title}`;
        },
        repeatInsert(input) {
            const newInputs = JSON.parse(JSON.stringify(input.inputs));
            input.cache = input.cache || [];
            input.cache.push(newInputs);
            this.onChangeForm();
        },
        repeatDelete(input, cacheId) {
            input.cache.splice(cacheId, 1);
            this.onChangeForm();
        },
    },
};
</script>

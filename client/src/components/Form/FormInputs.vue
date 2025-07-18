<template>
    <div>
        <div
            v-for="(input, index) in inputs"
            :key="index"
            :class="{ 'bordered-input': syncWithGraph && activeNodeId === index }">
            <div v-if="input.type == 'conditional'" class="ui-portlet-section mt-3">
                <div class="portlet-header">
                    <b>{{ input.test_param.label || input.test_param.name }}</b>
                </div>
                <div class="portlet-content">
                    <FormElement
                        :id="conditionalPrefix(input, input.test_param.name)"
                        v-model="input.test_param.value"
                        :type="input.test_param.type"
                        :help="input.test_param.help"
                        :help-format="input.test_param.help_format"
                        :refresh-on-change="false"
                        :disabled="sustainConditionals"
                        :attributes="input.test_param"
                        @change="onChange" />
                    <div v-for="(caseDetails, caseId) in input.cases" :key="caseId">
                        <FormNode
                            v-if="conditionalMatch(input, caseId)"
                            v-bind="$props"
                            :inputs="caseDetails.inputs"
                            :prefix="getPrefix(input.name)" />
                    </div>
                </div>
            </div>
            <div v-else-if="input.type == 'repeat'">
                <FormRepeat
                    :input="input"
                    :sustain-repeats="sustainRepeats"
                    :passthrough-props="$props"
                    :prefix="prefix"
                    @insert="() => repeatInsert(input)"
                    @delete="(id) => repeatDelete(input, id)"
                    @swap="(a, b) => repeatSwap(input, a, b)" />
            </div>
            <div v-else-if="input.type == 'section'">
                <FormCard :title="input.title || input.name" :expanded.sync="input.expanded" :collapsible="true">
                    <template v-slot:body>
                        <div v-if="input.help" class="my-2" data-description="section help">{{ input.help }}</div>
                        <FormNode v-bind="$props" :inputs="input.inputs" :prefix="getPrefix(input.name)" />
                    </template>
                </FormCard>
            </div>
            <FormElement
                v-else
                :id="getPrefix(input.name)"
                v-model="input.value"
                :title="input.label || input.name"
                :type="input.type"
                :error="input.error"
                :warning="input.warning"
                :help="input.help"
                :help-format="input.help_format"
                :refresh-on-change="input.refresh_on_change"
                :attributes="input.attributes || input"
                :collapsed-enable-text="collapsedEnableText"
                :collapsed-enable-icon="collapsedEnableIcon"
                :collapsed-disable-text="collapsedDisableText"
                :collapsed-disable-icon="collapsedDisableIcon"
                :loading="loading"
                :workflow-building-mode="workflowBuildingMode"
                :workflow-run="workflowRun"
                @change="onChange">
                <template v-slot:workflow-run-form-title-badges>
                    <FormInputMismatchBadge v-if="valMismatches(input.name)" @stop-flagging="$emit('stop-flagging')" />
                </template>
                <template v-slot:workflow-run-form-title-items>
                    <GButton
                        v-if="syncWithGraph"
                        size="small"
                        color="blue"
                        transparent
                        :title="activeNodeId === index ? 'Active' : 'View in Graph'"
                        :disabled="activeNodeId === index"
                        @click="$emit('update:active-node-id', index)">
                        <span class="fas fa-sitemap" />
                        <span class="fas fa-arrow-right" />
                    </GButton>
                </template>
            </FormElement>
        </div>
    </div>
</template>

<script>
import { set } from "vue";

import { matchCase } from "@/components/Form/utilities";

import FormInputMismatchBadge from "./Elements/FormInputMismatchBadge.vue";
import FormCard from "./FormCard.vue";
import FormRepeat from "./FormRepeat.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import FormElement from "@/components/Form/FormElement.vue";

export default {
    name: "FormNode",
    components: {
        FormCard,
        FormElement,
        FormRepeat,
        FormInputMismatchBadge,
        GButton,
    },
    props: {
        inputs: {
            type: Array,
            default: null,
        },
        loading: {
            type: Boolean,
            default: false,
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
        collapsedEnableText: {
            type: String,
            default: null,
        },
        collapsedDisableText: {
            type: String,
            default: null,
        },
        collapsedEnableIcon: {
            type: String,
            default: null,
        },
        collapsedDisableIcon: {
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
        workflowBuildingMode: {
            type: Boolean,
            default: false,
        },
        workflowRun: {
            type: Boolean,
            default: false,
        },
        activeNodeId: {
            type: Number,
            default: null,
        },
        syncWithGraph: {
            type: Boolean,
            default: false,
        },
        stepsNotMatchingRequest: {
            type: Array,
            default: () => [],
        },
    },
    methods: {
        getPrefix(name, index) {
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
        repeatInsert(input) {
            const newInputs = structuredClone(input.inputs);

            set(input, "cache", input.cache ?? []);
            input.cache.push(newInputs);

            this.onChangeForm();
        },
        repeatDelete(input, cacheId) {
            input.cache.splice(cacheId, 1);
            this.onChangeForm();
        },
        repeatSwap(input, a, b) {
            const tmpA = input.cache[a];
            const tmpB = input.cache[b];

            input.cache.splice(a, 1, tmpB);
            input.cache.splice(b, 1, tmpA);

            this.onChangeForm();
        },
        valMismatches(name) {
            return this.workflowRun && this.stepsNotMatchingRequest.map((step) => step.toString()).includes(name);
        },
    },
};
</script>

<style scoped>
.bordered-input {
    border: 1px solid blue;
    border-radius: 0.25rem;
}
</style>

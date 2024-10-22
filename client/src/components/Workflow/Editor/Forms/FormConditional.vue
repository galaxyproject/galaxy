<script setup lang="ts">
import { computed } from "vue";

import type { Step } from "@/stores/workflowStepStore";

import FormElement from "@/components/Form/FormElement.vue";

const emit = defineEmits<{
    (e: "onUpdateStep", id: number, value: Partial<Step>): void;
}>();
const props = defineProps<{
    step: Step;
}>();

const conditionalDefined = computed(() => {
    return Boolean(props.step.when);
});

function onSkipBoolean(value: boolean) {
    if (props.step.when && value === false) {
        emit("onUpdateStep", props.step.id, { when: undefined });
    } else if (value === true && !props.step.when) {
        const when = "$(inputs.when)";
        const newStep = {
            when,
            input_connections: { ...props.step.input_connections, when: undefined },
        };
        emit("onUpdateStep", props.step.id, newStep);
    }
}
</script>

<template>
    <FormElement
        id="__conditional"
        :value="conditionalDefined"
        title="Conditionally skip step?"
        help="Set to true and connect a boolean parameter that determines whether the step should run. The step runs if the parameter value is true and will be skipped if the parameter value is false"
        type="boolean"
        @input="onSkipBoolean"></FormElement>
    <!-- We don't seem to have a disabled text field
        <FormElement
            v-if="setConditional"
            id="__when"
            :value="step.when"
            type="text"
            help="Step will be executed if javascript expression below evaluates to true."
            >
        </FormElement>
    -->
</template>

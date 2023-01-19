<script setup lang="ts">
import FormElement from "@/components/Form/FormElement.vue";
import { computed } from "vue";
import type { Step } from "@/stores/workflowStepStore";

const emit = defineEmits<{
    (e: "onUpdateStep", value: Step): void;
}>();
const props = defineProps<{
    step: Step;
}>();

const conditionalDefined = computed(() => {
    return Boolean(props.step.when);
});

function onSkipBoolean(value: boolean) {
    if (props.step.when && value === false) {
        emit("onUpdateStep", { ...props.step, when: undefined });
    } else if (value === true && !props.step.when) {
        const when = "${inputs.when}";
        const newStep = {
            ...props.step,
            when,
            input_connections: { ...props.step.input_connections, when: undefined },
        };
        emit("onUpdateStep", newStep);
    }
}
</script>

<template>
    <FormElement
        id="__conditional"
        :value="conditionalDefined"
        title="Conditionally skip step?"
        help="Set to true and connect a boolean parameter that determines whether step will be skipped"
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

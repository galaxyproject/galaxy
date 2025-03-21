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
        title="是否有条件地跳过步骤？"
        help="设置为真并连接一个布尔参数，该参数决定是否应该运行该步骤。如果参数值为真，则步骤运行；如果参数值为假，则步骤将被跳过"
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

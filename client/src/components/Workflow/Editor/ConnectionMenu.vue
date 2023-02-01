<template>
    <b-list-group id="input-choices-menu" ref="menu" role="menu" @keyup.down="increment" @keyup.up="decrement">
        <template v-if="allElements.length === 0">
            <b-list-group-item ref="menuItem" tabindex="0" role="menuitem">
                No compatible input found in workflow
            </b-list-group-item>
        </template>
        <template v-else>
            <b-list-group-item
                v-for="(input, index) in allElements"
                :key="input.inputLabel + input.stepId"
                ref="menuItem"
                role="menuitem"
                tabindex="0"
                :active="activeElement === index"
                @click="toggleConnection(input)"
                @keyup.enter="toggleConnection(input)"
                @focus="activeElement = index">
                {{ input.connected ? "Disconnect from" : "Connect to" }} {{ input.inputLabel }}
            </b-list-group-item>
        </template>
    </b-list-group>
</template>
<script lang="ts" setup>
import { useWorkflowStepStore } from "@/stores/workflowStepStore";
import { computed, onMounted, ref, watch, type ComputedRef } from "vue";
import {
    type OutputTerminals,
    type InputTerminalsAndInvalid,
    terminalFactory,
    type InputTerminals,
} from "./modules/terminals";
import { useFocusWithin } from "@/composables/useActiveElement";
import { assertDefined } from "@/utils/assertions";

const props = defineProps<{
    terminal: OutputTerminals;
}>();

const menu = ref();
const { focused } = useFocusWithin(menu);

const activeElement = ref(0);
const menuItem = ref<HTMLLIElement[] | HTMLLIElement>();
const emit = defineEmits<{ (e: "closeMenu", value: boolean): void }>();

onMounted(() => {
    if (menuItem.value) {
        if ("length" in menuItem.value) {
            menuItem.value[0]?.focus();
        } else {
            menuItem.value.focus();
        }
    }
});

watch(focused, (focused) => {
    if (!focused) {
        emit("closeMenu", true);
    }
});

const stepStore = useWorkflowStepStore();

interface InputObject {
    stepId: number;
    inputName: string;
    inputLabel: string;
    connected: boolean;
}

function increment() {
    if (menuItem.value && "length" in menuItem.value) {
        activeElement.value += 1;
        activeElement.value = Math.min(activeElement.value, menuItem.value!.length - 1);
        menuItem.value![activeElement.value]?.focus();
    }
}

function decrement() {
    if (menuItem.value && "length" in menuItem.value) {
        activeElement.value = Math.max(activeElement.value - 1, 0);
        menuItem.value![activeElement.value]?.focus();
    }
}

function terminalToInputObject(terminal: InputTerminalsAndInvalid, connected: boolean): InputObject {
    const step = stepStore.getStep(terminal.stepId);
    assertDefined(step);
    const inputLabel = `${terminal.name} in step ${step.id + 1}: ${step.label}`;
    return { stepId: step.id, inputName: terminal.name, inputLabel, connected };
}

function inputObjectToTerminal(inputObject: InputObject): InputTerminals {
    const step = stepStore.getStep(inputObject.stepId);
    assertDefined(step);
    const inputSource = step.inputs.find((input) => input.name == inputObject.inputName)!;
    return terminalFactory(inputObject.stepId, inputSource, props.terminal.datatypesMapper);
}

const validInputs: ComputedRef<InputObject[]> = computed(() => {
    const inputTerminals = props.terminal.validInputTerminals();
    return inputTerminals.map((inputTerminal) => terminalToInputObject(inputTerminal, false));
});

const connectedInputs: ComputedRef<InputObject[]> = computed(() => {
    const inputTerminals = props.terminal.getConnectedTerminals();
    return inputTerminals.map((inputTerminal) => terminalToInputObject(inputTerminal, true));
});

const allElements = computed(() => {
    const allElements = [...connectedInputs.value, ...validInputs.value];
    allElements.sort((elementA, elementB) => {
        const stepIdSort = elementA.stepId - elementB.stepId;
        if (stepIdSort === 0) {
            return (elementA.inputLabel || elementA.inputName) < (elementB.inputLabel || elementB.inputName) ? -1 : 1;
        }
        return stepIdSort;
    });
    return allElements;
});

function toggleConnection(inputObject: InputObject) {
    if (inputObject.connected) {
        inputObjectToTerminal(inputObject).disconnect(props.terminal);
    } else {
        inputObjectToTerminal(inputObject).connect(props.terminal);
    }
}
</script>

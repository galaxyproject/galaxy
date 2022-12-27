<template>
    <b-list-group ref="menu" id="input-choices-menu" role="menu" @keyup.down="increment" @keyup.up="decrement">
        <b-list-group-item
            v-for="(input, index) in allElements"
            role="menu-item"
            ref="menuItem"
            @click="toggleConnection(input)"
            @keyup.enter="toggleConnection(input)"
            @focus="activeElement = index"
            :tabindex="index + 1"
            :active="activeElement === index">
            {{ input.connected ? "Disconnect" : "Connect" }} to {{ input.inputLabel }}
        </b-list-group-item>
    </b-list-group>
</template>
<script lang="ts" setup>
import { useWorkflowStepStore } from "@/stores/workflowStepStore";
import { computed, nextTick, onMounted, ref, watch, type ComputedRef } from "vue";
import { type OutputTerminals, type InputTerminals, terminalFactory } from "./modules/terminals";
import { useFocusWithin } from "@/composables/useActiveElement";

const props = defineProps<{
    terminal: OutputTerminals;
}>();

const menu = ref();
const { focused } = useFocusWithin(menu);

const activeElement = ref(0);
const menuItem = ref<HTMLLIElement[]>();
const emit = defineEmits<{ (e: "closeMenu", value: boolean): void }>();

onMounted(() => {
    menuItem.value![0].focus();
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
    console.log("incr");
    activeElement.value += 1;
    activeElement.value = Math.min(activeElement.value, menuItem.value!.length - 1);
    menuItem.value![activeElement.value].focus();
}

function decrement() {
    console.log("decr");
    activeElement.value = Math.max(activeElement.value - 1, 0);
    menuItem.value![activeElement.value].focus();
}

function terminalToInputObject(terminal: InputTerminals, connected: boolean): InputObject {
    const step = stepStore.getStep(terminal.stepId);
    const inputLabel = `${terminal.name} in step ${step.id + 1}: ${step.label}`;
    return { stepId: step.id, inputName: terminal.name, inputLabel, connected };
}

function inputObjectToTerminal(inputObject: InputObject): InputTerminals {
    const inputSource = stepStore
        .getStep(inputObject.stepId)
        .inputs.find((input) => input.name == inputObject.inputName)!;
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

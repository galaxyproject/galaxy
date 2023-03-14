<script setup lang="ts">
import { STATES } from "./states";
import type { ComputedRef } from "vue";
import { computed } from "vue";

type State = {
    status: string;
    text?: string;
    icon?: string;
    spin?: boolean;
};
interface States {
    [key: string]: State;
}
interface HelpText {
    [key: string]: string;
}

const props = defineProps({
    showHelp: { type: Boolean, default: false },
});

const emit = defineEmits<{
    (e: "update:show-help", showHelp: boolean): void;
    (e: "set-filter", filter: string, value: string): void;
}>();

const propShowHelp = computed({
    get: () => {
        return props.showHelp;
    },
    set: (val) => {
        emit("update:show-help", val);
    },
});
const states: ComputedRef<States> = computed(() => STATES);

const helpText: HelpText = {
    failed: "The dataset failed to run.",
    ok: "The dataset has no errors and is useable and readable in the history.",
};

function onFilter(value: string) {
    propShowHelp.value = false;
    emit("set-filter", `state:`, value);
}
</script>

<template>
    <b-modal v-model="propShowHelp" title="History Item States Help" ok-only>
        <p>Here are all available item states in Galaxy:</p>
        <p><i>(Note that the colors for each state correspond to content item state colors in the history)</i></p>
        <dl v-for="(state, key, index) in states" :key="index">
            <b-alert :variant="state.status || 'success'" show>
                <dt>
                    <a href="javascript:void(0)" @click="onFilter(key)"
                        ><code>{{ key }}</code></a
                    >
                    <icon v-if="state.icon" :icon="state.icon" />
                </dt>
                <dd>{{ helpText[key] || state.text }}</dd>
            </b-alert>
        </dl>
    </b-modal>
</template>

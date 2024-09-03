<script setup lang="ts">
import { STATES } from "./states";
import type { HelpText, States } from "./stateTypes";

const props = defineProps({
    excludeStates: { type: Array<keyof typeof STATES>, required: false, default: () => ["empty", "failed", "upload"] },
});

const emit = defineEmits<{
    (e: "set-filter", filter: string, value: string): void;
}>();

const states = STATES as States;
const helpText: HelpText = {
    failed: "The job failed to run.",
    ok: "The dataset has no errors.",
};

if (props.excludeStates) {
    for (const state of props.excludeStates) {
        delete states[state];
    }
}

function dataState(state: string) {
    return state === "new_populated_state" ? "new" : state;
}

function onFilter(value: string) {
    emit("set-filter", `state`, value);
}
</script>

<template>
    <div>
        <p>Here are all available item states in Galaxy:</p>
        <p>
            <i>
                (Note that the colors for each state correspond to content item state colors in the history, and if it
                exists, hovering over the icon on a history item will display the state message.)
            </i>
            <br />
            <b>You cannot filter a history for collections given a state.</b>
        </p>
        <dl v-for="(state, key, index) in states" :key="index">
            <div :class="['alert', 'content-item', 'alert-' + state.status]" :data-state="dataState(key)">
                <dt>
                    <a v-if="!state.nonDb" class="text-decoration-none" href="javascript:void(0)" @click="onFilter(key)"
                        ><code>{{ key }}</code></a
                    >
                    <span v-else
                        ><code>{{ key }}</code></span
                    >
                    <icon v-if="state.icon" :icon="state.icon" />
                </dt>
                <dd>{{ helpText[key] || state.text }}</dd>
            </div>
        </dl>
    </div>
</template>

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

function onFilter(value: string) {
    emit("set-filter", `state`, value);
}
</script>

<template>
    <div>
        <p>Here are all available item states in Galaxy:</p>
        <p><i>(Note that the colors for each state correspond to content item state colors in the history)</i></p>
        <dl v-for="(state, key, index) in states" :key="index">
            <div :class="['alert', 'content-item', 'alert-' + state.status]" :data-state="key">
                <dt>
                    <a class="text-decoration-none" href="javascript:void(0)" @click="onFilter(key)"
                        ><code>{{ key }}</code></a
                    >
                    <icon v-if="state.icon" :icon="state.icon" />
                </dt>
                <dd>{{ helpText[key] || state.text }}</dd>
            </div>
        </dl>
    </div>
</template>

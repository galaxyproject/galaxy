<script setup lang="ts">
import { BAlert, BLink, BProgress } from "bootstrap-vue";
import { ref, watch } from "vue";

import { useLocalPreferences } from "@/stores/localPreferencesStore";

interface Props {
    querySelectionBreak: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    querySelectionBreak: true,
});

const { hideSelectionQueryBreakWarning } = useLocalPreferences();

const dismissSecs = ref(10);
const dismissCountDown = ref(0);

function onDismissed() {
    dismissCountDown.value = 0;
}

function onDoNotShowAgain() {
    onDismissed();
    hideSelectionQueryBreakWarning.value = true;
}

watch(
    () => props.querySelectionBreak,
    () => {
        dismissCountDown.value = hideSelectionQueryBreakWarning ? 0 : dismissSecs.value;
    }
);
</script>

<template>
    <BAlert
        class="m-2"
        variant="info"
        :show="dismissCountDown"
        dismissible
        fade
        @dismissed="onDismissed"
        @dismiss-count-down="dismissCountDown = $event">
        <b>Please notice your selection has changed.</b> Manually unselecting items or adding new ones will disable the
        `select all` status.
        <BProgress variant="info" :max="dismissSecs" :value="dismissCountDown" height="4px" />
        <BLink @click="onDoNotShowAgain">Do not show again</BLink>
    </BAlert>
</template>

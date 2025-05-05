<script setup lang="ts">
import { BAlert, BLink, BProgress } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { ref, watch } from "vue";

import { useUserFlagsStore } from "@/stores/userFlagsStore";

interface Props {
    querySelectionBreak: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    querySelectionBreak: true,
});

const userFlagsStore = useUserFlagsStore();
const { showSelectionQueryBreakWarning } = storeToRefs(useUserFlagsStore());

const dismissSecs = ref(10);
const dismissCountDown = ref(0);

function onDismissed() {
    dismissCountDown.value = 0;
}

function onDoNotShowAgain() {
    onDismissed();
    userFlagsStore.ignoreSelectionQueryBreakWarning();
}

watch(
    () => props.querySelectionBreak,
    () => {
        dismissCountDown.value = showSelectionQueryBreakWarning.value ? dismissSecs.value : 0;
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

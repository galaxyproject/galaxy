<template>
    <GAlert
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
    </GAlert>
</template>

<script>
import { BLink, BProgress } from "bootstrap-vue";
import { mapActions, mapState } from "pinia";

import { useUserFlagsStore } from "@/stores/userFlagsStore";

import GAlert from "@/component-library/GAlert.vue";

export default {
    components: {
        GAlert,
        BLink,
        BProgress,
    },
    props: {
        querySelectionBreak: { type: Boolean, required: true },
    },
    data() {
        return {
            dismissSecs: 10,
            dismissCountDown: 0,
        };
    },
    computed: {
        ...mapState(useUserFlagsStore, ["getShowSelectionQueryBreakWarning"]),
    },
    watch: {
        querySelectionBreak() {
            this.dismissCountDown = this.getShowSelectionQueryBreakWarning() ? this.dismissSecs : 0;
        },
    },
    methods: {
        ...mapActions(useUserFlagsStore, ["ignoreSelectionQueryBreakWarning"]),
        onDismissed() {
            this.dismissCountDown = 0;
        },
        onDoNotShowAgain() {
            this.onDismissed();
            this.ignoreSelectionQueryBreakWarning();
        },
    },
};
</script>

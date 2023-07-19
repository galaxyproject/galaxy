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
        <GLink @click="onDoNotShowAgain">Do not show again</GLink>
    </GAlert>
</template>

<script>
import { BProgress } from "bootstrap-vue";
import { mapActions, mapState } from "pinia";

import { GAlert, GLink } from "@/component-library";
import { useUserFlagsStore } from "@/stores/userFlagsStore";

export default {
    components: {
        GAlert,
        GLink,
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

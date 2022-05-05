<template>
    <b-alert
        class="m-2"
        variant="info"
        :show="dismissCountDown"
        dismissible
        fade
        @dismissed="onDismissed"
        @dismiss-count-down="dismissCountDown = $event">
        <b>Please notice your selection has changed.</b> Manually unselecting items or adding new ones will disable the
        `select all` status.
        <b-progress variant="info" :max="dismissSecs" :value="dismissCountDown" height="4px" />
        <b-link @click="onDoNotShowAgain">Do not show again</b-link>
    </b-alert>
</template>

<script>
import { mapGetters, mapActions } from "vuex";
import { BAlert, BLink, BProgress } from "bootstrap-vue";
export default {
    components: {
        "b-alert": BAlert,
        "b-link": BLink,
        "b-progress": BProgress,
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
        ...mapGetters("userFlags", ["getShowSelectionQueryBreakWarning"]),
    },
    watch: {
        querySelectionBreak() {
            this.dismissCountDown = this.getShowSelectionQueryBreakWarning() ? this.dismissSecs : 0;
        },
    },
    methods: {
        ...mapActions("userFlags", ["ignoreSelectionQueryBreakWarning"]),
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

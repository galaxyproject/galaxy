<template>
    <IconButton
        v-if="stateIcon"
        v-b-tooltip
        :title="theTitle"
        :icon="stateIcon"
        :variant="variant"
        v-on="$listeners"
        v-bind="$attrs" />
</template>

<script>
import capitalize from "underscore.string/capitalize";
import IconButton from "components/IconButton";

export default {
    inject: ["STATES"],
    components: {
        IconButton,
    },
    props: {
        state: { type: String, required: true },
        variant: { type: String, required: false, default: "link" },
    },
    computed: {
        stateIcon() {
            if (this.inState(this.STATES.QUEUED, this.STATES.NEW, this.STATES.RUNNING)) {
                return "clock";
            }
            if (this.inState(this.STATES.PAUSED)) {
                return "pause";
            }
            if (this.inState(this.STATES.ERROR)) {
                return "exclamation-triangle";
            }
            if (this.inState(this.STATES.MIXED)) {
                return "exclamation-circle";
            }
            if (this.inState(this.STATES.OK)) {
                return "check";
            }
            return null;
        },
        theTitle() {
            return this.title || capitalize(this.state);
        },
    },
    methods: {
        inState(...states) {
            return states.includes(this.state);
        },
    },
};
</script>

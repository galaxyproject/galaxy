<template>
    <StateBtn
        v-if="inState(STATES.RUNNING)"
        :state="state"
        icon="upload-symbol upload-icon fa fa-spinner fa-spin"
        v-on="$listeners"
    />

    <StateBtn v-else-if="inState(STATES.QUEUED, STATES.NEW)" :state="state" icon="fas fa-clock" v-on="$listeners" />

    <StateBtn v-else-if="inState(STATES.PAUSED)" :state="state" icon="fas fa-pause" v-on="$listeners" />

    <StateBtn v-else-if="inState(STATES.ERROR)" :state="state" icon="fas fa-exclamation-triangle" v-on="$listeners" />

    <StateBtn v-else-if="inState(STATES.MIXED)" :state="state" icon="fas fa-exclamation-circle" v-on="$listeners" />

    <span v-else class="sr-only">
        {{ state | localize }}
    </span>
</template>

<script>
import capitalize from "underscore.string/capitalize";

export const StateBtn = {
    template: `
        <b-button class="state-button"
            v-b-tooltip
            :title="theTitle | localize"
            size="sm"
            variant="link"
            v-on="$listeners"
            v-bind="$attrs">
            <i :class="icon" />
            <span class="sr-only">{{ theTitle | localize }}</span>
        </b-button>
    `,
    props: {
        state: { type: String, required: true },
        icon: { type: String, required: true },
        title: { type: String, required: false, default: "" },
    },
    inject: ["STATES"],
    computed: {
        theTitle() {
            return this.title || capitalize(this.state);
        },
    },
};

export const StatusIcon = {
    components: {
        StateBtn,
    },
    props: {
        state: { type: String, required: true },
    },
    inject: ["STATES"],
    methods: {
        inState(...states) {
            return states.includes(this.state);
        },
    },
};

export default StatusIcon;
</script>

<style lang="css">
/* Override ham-fisted base css rules */

button.state-button,
button.state-button.disabled,
button.state-button:disabled,
button.state-button:focus,
button.state-button:hover,
button.state-button:not(:disabled):active {
    background-color: transparent !important;
    border-style: none !important;
    box-shadow: none !important;
}
</style>

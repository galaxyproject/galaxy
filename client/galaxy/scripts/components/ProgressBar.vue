<template>
    <div class="progress state-progress">
        <span class="note" v-if="note">
            {{ note }}<span v-if="loading">.<span class="blinking">..</span> </span>
        </span>
        <div class="progress-bar info" v-bind:style="infoStyle"></div>
        <div class="progress-bar ok" v-bind:style="okStyle"></div>
        <div class="progress-bar running" v-bind:style="runningStyle"></div>
        <div class="progress-bar new" v-bind:style="newStyle"></div>
    </div>
</template>
<script>
export default {
    props: {
        note: { type: String, default: null },
        loading: { type: Boolean, default: false },
        infoProgress: { type: Number, default: 0.0 },
        okProgress: { type: Number, default: 0.0 },
        runningProgress: { type: Number, default: 0.0 },
        newProgress: { type: Number, default: 0.0 }
    },
    computed: {
        infoStyle() {
            console.log(this.infoProgress);
            return { width: `${this.infoProgress * 100}%` };
        },
        newStyle() {
            return { width: `${this.newProgress * 100}%` };
        },
        runningStyle() {
            return { width: `${this.runningProgress * 100}%` };
        },
        okStyle() {
            return { width: `${this.okProgress * 100}%` };
        }
    }
};
</script>

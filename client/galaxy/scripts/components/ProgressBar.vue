<template>
    <div class="progress state-progress">
        <span class="note" v-if="note">
            {{ note }}<span v-if="loading">.<span class="blinking">..</span> </span>
        </span>
        <div class="progress-bar info" :style="styleFromProgress(infoProgress)" :title="infoMessage"></div>
        <div class="progress-bar ok" :style="styleFromProgress(okProgress)" :title="okMessage"></div>
        <div class="progress-bar running" :style="styleFromProgress(runningProgress)" :title="runningMessage"></div>
        <div class="progress-bar new" :style="styleFromProgress(newProgress)" :title="newMessage"></div>
        <div class="progress-bar error" :style="styleFromProgress(errorProgress)" :title="errorMessage"></div>
    </div>
</template>
<script>
// Not really a very generic ProgressBar - consider renaming to StateProgressBar.
export default {
    props: {
        note: { type: String, default: null },
        loading: { type: Boolean, default: false },
        infoProgress: { type: Number, default: 0.0 },
        infoMessage: { type: String, default: null },
        okProgress: { type: Number, default: 0.0 },
        okMessage: { type: String, default: null },
        runningProgress: { type: Number, default: 0.0 },
        runningMessage: { type: String, default: null },
        newProgress: { type: Number, default: 0.0 },
        newMessage: { type: String, default: null },
        errorProgress: { type: Number, default: 0.0 },
        errorMessage: { type: String, default: null },
    },
    methods: {
        styleFromProgress: function (progress) {
            return { width: `${progress * 100}%` };
        },
    },
};
</script>

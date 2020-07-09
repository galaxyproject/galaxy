<template>
    <div>
        <small class="note" v-if="note">
            {{ note }}<span v-if="loading">.<span class="blinking">..</span></span>
        </small>
        <b-progress :max="total">
            <b-progress-bar variant="warning" :value="infoCount" show-value />
            <b-progress-bar variant="warning" :value="runningCount" show-value />
            <b-progress-bar variant="success" :value="okCount" show-value />
            <b-progress-bar variant="warning" :value="newCount" show-value />
            <b-progress-bar variant="danger" :value="errorCount" show-value />
        </b-progress>
    </div>
</template>
<script>
// Not really a very generic ProgressBar - consider renaming to StateProgressBar.
export default {
    props: {
        total: {
            type: Number,
            default: 1,
        },
        note: {
            type: String,
            default: null,
        },
        loading: {
            type: Boolean,
            default: false,
        },
        infoCount: {
            type: Number,
            default: 0,
        },
        okCount: {
            type: Number,
            default: 0,
        },
        runningCount: {
            type: Number,
            default: 0,
        },
        newCount: {
            type: Number,
            default: 0,
        },
        errorCount: {
            type: Number,
            default: 0,
        },
    },
};
</script>

<template>
    <div class="my-1 progressContainer">
        <small v-if="note" class="progressNote">
            {{ note }}<span v-if="loading">.<span class="blinking">..</span></span>
        </small>
        <b-progress :max="total">
            <GProgressBar variant="success" :value="okCount" />
            <GProgressBar variant="danger" :value="errorCount" />
            <GProgressBar variant="warning" :value="runningCount" />
            <GProgressBar variant="warning" :value="newCount" />
        </b-progress>
    </div>
</template>
<script>
// Not really a very generic ProgressBar - consider renaming to StateProgressBar.
import GProgressBar from "@/component-library/GProgressBar.vue";

export default {
    components: {
        GProgressBar,
    },
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
<style lang="css" scoped>
.progressNote {
    position: absolute;
    text-align: center;
    width: 100%;
}
.progressContainer {
    position: relative;
}
</style>

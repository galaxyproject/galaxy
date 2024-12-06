<script setup lang="ts">
// Not really a very generic ProgressBar - consider renaming to StateProgressBar.

import { BProgress, BProgressBar } from "bootstrap-vue";

interface Props {
    total?: number;
    note: string;
    loading?: boolean;
    okCount?: number;
    runningCount?: number;
    newCount?: number;
    errorCount?: number;
}

const props = withDefaults(defineProps<Props>(), {
    total: 1,
    note: undefined,
    loading: false,
    okCount: 0,
    runningCount: 0,
    newCount: 0,
    errorCount: 0,
});
</script>

<template>
    <div class="my-1 progress-container">
        <small v-if="props.note" class="progress-note">
            {{ props.note }}<span v-if="props.loading">.<span class="blinking">..</span></span>
        </small>
        <BProgress :max="props.total">
            <BProgressBar variant="success" :value="props.okCount" />
            <BProgressBar variant="danger" :value="props.errorCount" />
            <BProgressBar variant="warning" :value="props.runningCount" />
            <BProgressBar variant="warning" :value="props.newCount" />
        </BProgress>
    </div>
</template>

<style scoped>
.progress-note {
    position: absolute;
    text-align: center;
    width: 100%;
}
.progress-container {
    position: relative;
}
</style>

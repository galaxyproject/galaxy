<script setup lang="ts">
interface LoadingProps {
    message?: string
}

withDefaults(defineProps<LoadingProps>(), {
    message: "Loading",
})
</script>

<template>
    <div class="q-pa-md">
        <div class="fit q-gutter-md row">
            <q-spinner color="info" size="4em" :thickness="10" />
            <span class="loading-message text-info" style="font-size: 2em"
                >{{ message }}.<span class="blinking">..</span></span
            >
        </div>
    </div>
</template>

<style scoped>
.blinking {
    animation: blinker 1s linear infinite;
}

@keyframes blinker {
    50% {
        opacity: 0;
    }
}
</style>

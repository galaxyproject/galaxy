<script setup lang="ts">
// TODO -- Pretty this up a bit so it's not just a barebones Alert, include
// general client error verbiage and admin/help contact protocol below.
//
// Right now this is only used as a destination for navigation failures
// (AdminRequired), but could be used for other client errors that need to be
// presented to the user interrupting the normal flow and context of the app.

import Alert from "@/components/Alert.vue";

const props = defineProps<{
    error: Error;
}>();
</script>
<template>
    <div class="container error-container"><Alert :message="props.error.message" variant="error" /></div>
</template>
<style scoped>
.error-container {
    margin: 4rem auto;
}
</style>

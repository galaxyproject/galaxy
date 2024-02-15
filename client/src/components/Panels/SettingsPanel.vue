<script setup lang="ts">
import ActivitySettings from "@/components/ActivityBar/ActivitySettings.vue";
import ActivityPanel from "@/components/Panels/ActivityPanel.vue";
</script>

<template>
    <ActivityPanel title="Settings" go-to-all-title="User Preferences" href="/user">
        <h3>Customize Activity Bar</h3>
        <ActivitySettings />
    </ActivityPanel>
</template>

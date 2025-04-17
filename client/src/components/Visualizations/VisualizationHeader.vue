<script setup lang="ts">
import { faEye } from "@fortawesome/free-solid-svg-icons";

import { type Plugin } from "@/api/plugins";
import { absPath } from "@/utils/redirect";

defineProps<{
    plugin: Plugin;
}>();
</script>

<template>
    <div class="d-flex">
        <div class="plugin-thumbnail mr-2">
            <img v-if="plugin.logo" alt="visualization" :src="absPath(plugin.logo)" />
            <icon v-else :icon="faEye" class="plugin-icon" />
        </div>
        <div class="text-break">
            <div class="plugin-list-title font-weight-bold">{{ plugin.html }}</div>
            <div class="plugin-list-text text-muted">{{ plugin.description }}</div>
        </div>
    </div>
</template>

<style lang="scss">
.plugin-thumbnail {
    img {
        width: 2rem;
    }
    .plugin-icon {
        font-size: 1.3rem;
        padding: 0.3rem;
    }
}
</style>

<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
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
            <FontAwesomeIcon v-else :icon="faEye" size="xl" class="p-1" />
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
}
</style>

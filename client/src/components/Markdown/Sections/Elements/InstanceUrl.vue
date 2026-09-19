<script setup lang="ts">
import ExternalLink from "@/components/ExternalLink.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

defineProps<{
    href?: string;
    title?: string;
    loading: boolean;
}>();
</script>

<template>
    <p>
        <LoadingSpan v-if="loading" message="Loading instance configuration" />
        <ExternalLink v-else-if="href" :href="href">
            {{ title ?? href }}
        </ExternalLink>
        <i v-else>Configuration value unset, please contact Galaxy admin.</i>
    </p>
</template>

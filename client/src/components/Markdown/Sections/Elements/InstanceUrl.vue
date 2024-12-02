<script setup lang="ts">
import { computed } from "vue";

import ExternalLink from "@/components/ExternalLink.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

interface InstanceUrlProps {
    href?: string;
    title?: string;
    loading: boolean;
}

const props = withDefaults(defineProps<InstanceUrlProps>(), {
    href: undefined,
    title: undefined,
});

const effectiveTitle = computed(() => {
    return props.title ? props.title : props.href;
});
</script>

<template>
    <p>
        <LoadingSpan v-if="props.loading" message="Loading instance configuration"> </LoadingSpan>
        <ExternalLink v-else-if="props.href" :href="props.href">
            {{ effectiveTitle }}
        </ExternalLink>
        <i v-else> Configuration value unset, please contact Galaxy admin. </i>
    </p>
</template>

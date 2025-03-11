<script setup lang="ts">
import { BBadge } from "bootstrap-vue";
import { computed } from "vue";

import ExternalLink from "@/components/ExternalLink.vue";

interface Props {
    doi: string;
}

const props = defineProps<Props>();

const doiLink = computed(() => `https://doi.org/${props.doi}`);
</script>

<template>
    <BBadge v-b-tooltip.hover.noninteractive class="doi-badge" size="sm" title="DOI link">
        <ExternalLink :href="doiLink">
            {{ props.doi }}
        </ExternalLink>
    </BBadge>
</template>

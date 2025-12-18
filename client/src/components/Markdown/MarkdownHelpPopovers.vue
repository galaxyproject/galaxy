<script setup lang="ts">
import type { HelpElementReference } from "@/components/Markdown/gxuris-types";

import HelpPopover from "@/components/Help/HelpPopover.vue";

interface Props {
    elements: HelpElementReference[];
}

defineProps<Props>();
</script>

<template>
    <span>
        <span v-for="(value, i) in elements" :key="i">
            <HelpPopover :target="value.element" :term="value.term" />
        </span>
    </span>
</template>

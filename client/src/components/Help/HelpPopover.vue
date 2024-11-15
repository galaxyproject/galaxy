<script setup lang="ts">
import { BPopover } from "bootstrap-vue";

import HelpTerm from "./HelpTerm.vue";

interface Props {
    target: any;
    term: string;
}

defineProps<Props>();
</script>

<template>
    <BPopover v-if="target" :target="target" triggers="hover" placement="bottom">
        <HelpTerm :term="term" />
    </BPopover>
</template>

<script setup lang="ts">
import HelpTerm from "./HelpTerm.vue";
import Popper from "@/components/Popper/Popper.vue";

interface Props {
    target: HTMLElement;
    term: string;
}

defineProps<Props>();
</script>

<template>
    <Popper v-if="target" :reference-el="target" mode="light">
        <HelpTerm :term="term" class="p-2" />
    </Popper>
</template>

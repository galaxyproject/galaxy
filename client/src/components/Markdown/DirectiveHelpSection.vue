<script setup lang="ts">
import DirectiveHelp from "./DirectiveHelp.vue";

interface DirectiveHelpSectionProps {
    directives: string[];
    mode: "page" | "report";
}

defineProps<DirectiveHelpSectionProps>();
</script>

<template>
    <dl>
        <DirectiveHelp v-for="directive in directives" :key="directive" :directive="directive" :mode="mode">
        </DirectiveHelp>
    </dl>
</template>

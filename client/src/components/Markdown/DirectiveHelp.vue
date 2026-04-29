<script setup lang="ts">
import { computed } from "vue";

import { directiveEntry } from "./directives";

interface DirectiveHelpProps {
    directive: string;
    mode: "page" | "report";
}

const props = defineProps<DirectiveHelpProps>();

const entry = computed(() => directiveEntry(props.directive, props.mode));
</script>

<template>
    <div>
        <dt>
            <tt>{{ directive }}</tt>
        </dt>
        <dd>{{ entry.help }}</dd>
    </div>
</template>

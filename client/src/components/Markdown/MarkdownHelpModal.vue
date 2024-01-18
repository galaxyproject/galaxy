<script setup lang="ts">
import { computed, ref } from "vue";

import MarkdownHelp from "./MarkdownHelp.vue";

interface MarkdownHelpModalProps {
    mode: "report" | "page";
}

const props = defineProps<MarkdownHelpModalProps>();

const show = ref(false);
const title = computed(() => {
    if (props.mode == "page") {
        return "Markdown Help for Pages";
    } else {
        return "Markdown Help for Invocation Reports";
    }
});

function showMarkdownHelp() {
    show.value = true;
}

defineExpose({
    showMarkdownHelp,
});
</script>

<template>
    <b-modal v-model="show" hide-footer>
        <template v-slot:modal-title>
            <h2 class="mb-0">{{ title }}</h2>
        </template>
        <MarkdownHelp :mode="mode" />
    </b-modal>
</template>

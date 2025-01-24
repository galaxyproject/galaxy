<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import { markup } from "@/components/ObjectStore/configurationMarkdown";
import { getAppRoot } from "@/onload/loadConfig";

import HelpPopover from "@/components/Help/HelpPopover.vue";

const props = defineProps<{
    content: string;
}>();

const markdownHtml = computed(() => markup(props.content ?? "", false));

const helpHtml = ref<HTMLDivElement>();

interface InternalTypeReference {
    element: HTMLElement;
    term: string;
}

const internalHelpReferences = ref<InternalTypeReference[]>([]);

function setupPopovers() {
    internalHelpReferences.value.length = 0;
    if (helpHtml.value) {
        const links = helpHtml.value.getElementsByTagName("a");
        Array.from(links).forEach((link) => {
            if (link.href.startsWith("gxhelp://")) {
                const uri = link.href.substr("gxhelp://".length);
                internalHelpReferences.value.push({ element: link, term: uri });
                link.href = `${getAppRoot()}help/terms/${uri}`;
                link.style.color = "inherit";
                link.style.textDecorationLine = "underline";
                link.style.textDecorationStyle = "dashed";
            }
        });
    }
}

onMounted(setupPopovers);
</script>

<template>
    <span>
        <!-- Disable v-html warning because we allow markdown generated HTML
            in various places in the Galaxy interface. Raw HTML is not allowed
            here because admin = false in the call to markup.
        -->
        <!-- eslint-disable-next-line vue/no-v-html -->
        <div ref="helpHtml" v-html="markdownHtml" />
        <span v-for="(value, i) in internalHelpReferences" :key="i">
            <HelpPopover :target="value.element" :term="value.term" />
        </span>
    </span>
</template>

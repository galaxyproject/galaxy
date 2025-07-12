<script setup lang="ts">
import "vue-json-pretty/lib/styles.css";

import { computed } from "vue";
import VueJsonPretty from "vue-json-pretty";

import { useHelpTermsStore } from "@/stores/helpTermsStore";

import HelpText from "@/components/Help/HelpText.vue";

const { hasHelpText } = useHelpTermsStore();

interface Props {
    parameterValue: string | object;
}

const props = defineProps<Props>();

const jsonData = computed(() => {
    if (typeof props.parameterValue === "string") {
        return JSON.parse(props.parameterValue);
    }
    return props.parameterValue;
});

function shouldLink(key: string): boolean {
    return hasHelpText(`galaxy.dataFetch.${key}`);
}
</script>

<template>
    <VueJsonPretty :data="jsonData" :virtual="false">
        <template v-slot:nodeKey="{ node, defaultKey }">
            <span v-if="shouldLink(node.key)">
                "<HelpText :uri="`galaxy.dataFetch.${node.key}`" :text="node.key" />"
            </span>
            <span v-else>
                {{ defaultKey }}
            </span>
        </template>
        <template v-slot:nodeValue="{ node, defaultValue }">
            <span v-if="node.path.endsWith('destination.type')">
                "<HelpText :uri="`galaxy.dataFetch.destinations.${node.content}`" :text="node.content" />"
            </span>
            <span v-else-if="node.path.endsWith('.src') && shouldLink(`sources.${node.content}`)">
                "<HelpText :uri="`galaxy.dataFetch.sources.${node.content}`" :text="node.content" />"
            </span>
            <span v-else-if="node.path.endsWith('.ext')">
                "<HelpText :uri="`galaxy.datatypes.extensions.${node.content}`" :text="node.content" />"
            </span>
            <span v-else>
                {{ defaultValue }}
            </span>
        </template>
    </VueJsonPretty>
</template>

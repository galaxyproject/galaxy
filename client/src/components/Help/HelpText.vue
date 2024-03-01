<script setup lang="ts">
import { computed } from "vue";

import { hasHelp as hasHelpText, help as helpText } from "./terms";

import ConfigurationMarkdown from "@/components/ObjectStore/ConfigurationMarkdown.vue";

interface Props {
    uri: string;
    text: string;
}

const props = defineProps<Props>();

const hasHelp = computed<boolean>(() => {
    return hasHelpText(props.uri);
});

const help = computed<string>(() => {
    return helpText(props.uri) as string;
});
</script>

<template>
    <span>
        <b-popover
            v-if="hasHelp"
            :target="
                () => {
                    return $refs.helpTarget;
                }
            "
            triggers="hover"
            placement="bottom">
            <ConfigurationMarkdown :markdown="help" :admin="true" />
        </b-popover>
        <span v-if="hasHelp" ref="helpTarget" class="help-text">{{ text }}</span>
        <span v-else>{{ text }}</span>
    </span>
</template>

<style scoped>
/* Give visual indication of mouseover info */
.help-text {
    text-decoration-line: underline;
    text-decoration-style: dashed;
}
</style>

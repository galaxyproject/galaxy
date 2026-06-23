<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { toRef } from "vue";

import { useHelpForTerm } from "@/stores/helpTermsStore";

import LoadingSpan from "@/components/LoadingSpan.vue";
import ConfigurationMarkdown from "@/components/ObjectStore/ConfigurationMarkdown.vue";

interface Props {
    term: string;
}

const props = defineProps<Props>();

const { loading, hasHelp, help } = useHelpForTerm(toRef(props, "term"));
</script>

<template>
    <div>
        <div v-if="loading">
            <LoadingSpan message="Loading Galaxy help terms" />
        </div>
        <div v-else-if="hasHelp && help">
            <ConfigurationMarkdown :markdown="help" :admin="true" />
        </div>
        <div v-else>
            <BAlert variant="error"> Something went wrong, no Galaxy help found for term or URI {{ term }}. </BAlert>
        </div>
    </div>
</template>

<script setup lang="ts">
import { faDownload } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BCard, BCardTitle, BLink } from "bootstrap-vue";

// We use this in two capacities - one where we have to do a post and do complex things
// to generate the workbook and one where we just have an easy link. Support both.
interface Props {
    generateWorkbookLink?: string;
}

withDefaults(defineProps<Props>(), {
    generateWorkbookLink: undefined,
});

const emit = defineEmits(["download"]);
</script>

<template>
    <BCard>
        <BCardTitle>
            <b>Step 1: Download</b>
        </BCardTitle>
        <BLink :href="generateWorkbookLink" @click="emit('download')"
            ><FontAwesomeIcon size="xl" :icon="faDownload" /> Download workbook.</BLink
        >
    </BCard>
</template>

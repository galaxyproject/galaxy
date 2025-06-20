<script setup lang="ts">
import { faDownload } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BCard, BCardTitle, BLink } from "bootstrap-vue";

interface Props {
    generateWorkbookLink: string;
}

defineProps<Props>();
</script>

<template>
    <BCard>
        <BCardTitle>
            <b>Step 1: Download</b>
        </BCardTitle>
        <BLink :href="generateWorkbookLink"><FontAwesomeIcon size="xl" :icon="faDownload" /> Download workbook.</BLink>
    </BCard>
</template>

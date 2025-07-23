<script setup lang="ts">
import { faDownload } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BCard, BCardTitle, BLink } from "bootstrap-vue";

const emit = defineEmits(["download"]);
</script>

<template>
    <BCard>
        <BCardTitle>
            <b>Step 1: Download</b>
        </BCardTitle>
        <BLink @click="emit('download')"><FontAwesomeIcon size="xl" :icon="faDownload" /> Download workbook.</BLink>
    </BCard>
</template>

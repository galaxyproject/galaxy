<script setup lang="ts">
import { faEdit } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BCard, BCardTitle } from "bootstrap-vue";
</script>

<template>
    <BCard>
        <BCardTitle>
            <b>Step 2: Fill Out</b>
        </BCardTitle>
        <FontAwesomeIcon size="xl" :icon="faEdit" />Fill out the workbook with your favorite spreadsheet application and
        save it to your local disk.
    </BCard>
</template>

<script setup lang="ts">
import { faFileExcel } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";

interface Props {
    title: string;
}

defineProps<Props>();

const emit = defineEmits(["click"]);
</script>

<template>
    <BButton :title="title" role="button" variant="link" size="sm" class="ml-0" @click="emit('click')">
        <FontAwesomeIcon :icon="faFileExcel" />
    </BButton>
</template>

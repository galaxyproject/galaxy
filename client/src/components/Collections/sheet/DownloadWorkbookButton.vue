<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faFileExcel } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";

library.add(faFileExcel);

interface Props {
    title: string;
}

defineProps<Props>();

const emit = defineEmits(["click"]);
</script>

<template>
    <BButton :title="title" role="button" variant="link" size="sm" class="ml-0" @click="emit('click')">
        <FontAwesomeIcon icon="file-excel" />
    </BButton>
</template>

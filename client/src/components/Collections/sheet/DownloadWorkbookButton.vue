<script setup lang="ts">
import { faFileExcel } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

import GButton from "@/components/BaseComponents/GButton.vue";

interface Props {
    title: string;
}

defineProps<Props>();

const emit = defineEmits(["click"]);
</script>

<template>
    <GButton :title="title" role="button" icon-only size="small" class="ml-0" @click="emit('click')">
        <FontAwesomeIcon :icon="faFileExcel" />
    </GButton>
</template>

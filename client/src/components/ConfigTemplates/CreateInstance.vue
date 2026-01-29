<script lang="ts" setup>
import { BContainer } from "bootstrap-vue";

import LoadingSpan from "@/components/LoadingSpan.vue";

interface Props {
    loading: boolean;
    loadingMessage: string;
}

defineProps<Props>();
</script>

<template>
    <BContainer fluid class="p-0">
        <LoadingSpan v-if="loading" :message="loadingMessage" />
        <div v-else>
            <slot />
        </div>
    </BContainer>
</template>

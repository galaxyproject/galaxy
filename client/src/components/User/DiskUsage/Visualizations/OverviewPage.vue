<script setup lang="ts">
import localize from "@/utils/localization";

import Heading from "@/components/Common/Heading.vue";

interface Props {
    title: string;
}

defineProps<Props>();
</script>

<template>
    <div class="mx-3">
        <router-link :to="{ name: 'StorageDashboard' }">{{ localize("Back to Dashboard") }}</router-link>
        <Heading h1 bold class="my-3">{{ localize(title) }}</Heading>
        <slot />
    </div>
</template>

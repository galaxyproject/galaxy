<script setup lang="ts">
import { BAlert, BLink } from "bootstrap-vue";

import localize from "@/utils/localization";

const emit = defineEmits<{
    (e: "clicked-upload"): void;
}>();
</script>
<template>
    <BAlert variant="info" show>
        {{ localize("No items available to create a collection.") }}
        {{ localize("Exit and change your current history, or") }}
        <BLink class="text-decoration-none" @click.stop.prevent="emit('clicked-upload')">
            {{ localize("Upload some datasets.") }}
        </BLink>
    </BAlert>
</template>

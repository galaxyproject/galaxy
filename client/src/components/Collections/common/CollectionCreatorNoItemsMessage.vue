<script setup lang="ts">
import { BLink } from "bootstrap-vue";

import localize from "@/utils/localization";

import GAlert from "@/components/BaseComponents/GAlert.vue";

const emit = defineEmits<{
    (e: "click-upload"): void;
}>();
</script>
<template>
    <GAlert variant="info" show>
        {{ localize("No items available to create a collection.") }}
        {{ localize("Exit and change your current history, or") }}
        <BLink class="text-decoration-none" @click.stop.prevent="emit('click-upload')">
            {{ localize("Upload some datasets.") }}
        </BLink>
    </GAlert>
</template>

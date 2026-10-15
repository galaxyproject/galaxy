<script setup lang="ts">
import localize from "@/utils/localization";

import GAlert from "@/components/BaseComponents/GAlert.vue";
import GLink from "@/components/BaseComponents/GLink.vue";

const emit = defineEmits<{
    (e: "click-upload"): void;
}>();
</script>
<template>
    <GAlert variant="info" show>
        {{ localize("No items available to create a collection.") }}
        {{ localize("Exit and change your current history, or") }}
        <GLink @click.stop.prevent="emit('click-upload')">
            {{ localize("Upload some datasets.") }}
        </GLink>
    </GAlert>
</template>

<script setup lang="ts">
import { BCard, BCardTitle } from "bootstrap-vue";

import { borderVariant } from "@/components/Common/Wizard/utils";

interface Props {
    selected: boolean;
}

defineProps<Props>();

const emit = defineEmits(["select"]);
</script>

<template>
    <BCard
        data-import-source-from="remote_files"
        class="wizard-selection-card"
        :border-variant="borderVariant(selected)"
        @click="emit('select', 'remote_files')">
        <BCardTitle>
            <b>Remote Files</b>
        </BCardTitle>
        <div>This option lets you select a folder of file URIs from Galaxy's configured "remote file" sources.</div>
    </BCard>
</template>

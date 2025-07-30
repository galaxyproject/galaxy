<script setup lang="ts">
import { BCard, BCardTitle } from "bootstrap-vue";

import { borderVariant } from "@/components/Common/Wizard/utils";

interface Props {
    selected: boolean;
    forWhat: "rule_builder" | "sample_sheet";
}

withDefaults(defineProps<Props>(), {
    forWhat: "rule_builder",
});

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
        <div v-if="forWhat === 'rule_builder'">
            This option lets you select a folder of file URIs from Galaxy's configured "remote file" repositories.
        </div>
        <div v-else>Select a folder of file URIs from Galaxy's configured "remote file" repositories.</div>
    </BCard>
</template>

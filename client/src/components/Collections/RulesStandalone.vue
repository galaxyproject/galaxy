<script setup lang="ts">
import { BContainer, BRow } from "bootstrap-vue";
import { ref } from "vue";

import { useConfig } from "@/composables/config";

import BuildFileSetWizard from "./BuildFileSetWizard.vue";
import GAlert from "@/components/BaseComponents/GAlert.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const { config, isConfigLoaded } = useConfig();

const created = ref(false);

function onCreated() {
    created.value = true;
}
</script>

<template>
    <BContainer>
        <LoadingSpan v-if="!isConfigLoaded" />
        <BRow v-else-if="created">
            <GAlert show variant="success" style="width: 100%">
                Data imported and should be available in your history.
            </GAlert>
        </BRow>
        <div v-else>
            <BuildFileSetWizard
                mode="standalone"
                :file-sources-configured="config.file_sources_configured"
                :ftp-upload-site="config.ftp_upload_site"
                @created="onCreated" />
        </div>
    </BContainer>
</template>

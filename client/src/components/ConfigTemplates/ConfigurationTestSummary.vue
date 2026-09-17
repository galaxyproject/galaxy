<script lang="ts" setup>
import { BListGroup } from "bootstrap-vue";

import type { PluginStatus } from "@/api/configTemplates";

import ConfigurationTestItem from "./ConfigurationTestItem.vue";

interface Props {
    testResults?: PluginStatus;
}

defineProps<Props>();
</script>

<template>
    <BListGroup v-if="testResults">
        <ConfigurationTestItem :status="testResults?.template_definition" />
        <ConfigurationTestItem
            v-if="testResults?.oauth2_access_token_generation != null"
            :status="testResults?.oauth2_access_token_generation" />
        <ConfigurationTestItem :status="testResults?.template_settings ?? undefined" />
        <ConfigurationTestItem :status="testResults?.connection ?? undefined" />
    </BListGroup>
</template>

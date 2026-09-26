<script lang="ts" setup>
import { faCheckSquare, faSquare, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BListGroupItem } from "bootstrap-vue";

import type { PluginAspectStatus } from "@/api/configTemplates";

import LoadingSpan from "@/components/LoadingSpan.vue";

interface Props {
    status?: PluginAspectStatus;
}

defineProps<Props>();
</script>

<template>
    <BListGroupItem href="#" class="d-flex align-items-center">
        <LoadingSpan v-if="status == undefined" classes="mr-3" message="Testing" />
        <FontAwesomeIcon v-else-if="status?.state == 'ok'" class="mr-3 text-success" :icon="faCheckSquare" size="lg" />
        <FontAwesomeIcon v-else-if="status?.state == 'not_ok'" class="mr-3 text-warning" :icon="faTimes" size="lg" />
        <FontAwesomeIcon v-else-if="status?.state == 'unknown'" class="mr-3 text-info" :icon="faSquare" size="lg" />

        <span v-if="status && status.message" class="mr-auto">
            {{ status.message }}
        </span>
    </BListGroupItem>
</template>

<script lang="ts" setup>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCheckSquare, faSquare, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BListGroupItem, BSpinner } from "bootstrap-vue";

import type { PluginAspectStatus } from "@/api/configTemplates";

library.add(faCheckSquare, faTimes, faSquare);

interface Props {
    status?: PluginAspectStatus;
}

defineProps<Props>();
</script>

<template>
    <BListGroupItem href="#" class="d-flex align-items-center">
        <BSpinner v-if="status == undefined" class="mr-3" label="Testing...."></BSpinner>
        <FontAwesomeIcon
            v-else-if="status.state == 'ok'"
            class="mr-3 text-success"
            icon="fas fa-check-square"
            size="lg" />
        <FontAwesomeIcon v-else-if="status.state == 'not_ok'" class="mr-3 text-warning" icon="fas fa-times" size="lg" />
        <FontAwesomeIcon v-else-if="status.state == 'unknown'" class="mr-3 text-info" icon="fas fa-square" size="lg" />
        <span v-if="status && status.message" class="mr-auto">
            {{ status.message }}
        </span>
    </BListGroupItem>
</template>

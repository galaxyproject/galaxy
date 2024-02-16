<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faArchive } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";

import { bytesToString } from "@/utils/utils";

import type { DataValuePoint } from "./Charts";

library.add(faArchive);

interface RecoverableItemSizeTooltipProps {
    data: DataValuePoint;
    isRecoverable: boolean;
    isArchived?: boolean;
}

const props = withDefaults(defineProps<RecoverableItemSizeTooltipProps>(), {
    isArchived: false,
});

const label = computed(() => props.data?.label ?? "No data");
const prettySize = computed(() => bytesToString(props.data?.value ?? 0));
</script>
<template>
    <div>
        <div class="h-md mx-2">{{ label }}</div>
        <b class="h-md m-2">{{ prettySize }}</b>
        <div v-if="isArchived" class="text-muted mx-2"><FontAwesomeIcon icon="archive" /> This item is archived</div>
        <div v-if="isRecoverable" class="text-muted mx-2">Recoverable storage space</div>
    </div>
</template>

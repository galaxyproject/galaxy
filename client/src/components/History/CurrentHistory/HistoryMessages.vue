<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { computed, ref } from "vue";

import type { HistorySummary } from "@/api";
import localize from "@/utils/localization";

interface Props {
    history: HistorySummary;
}

const props = defineProps<Props>();

const userOverQuota = ref(false);

const hasMessages = computed(() => {
    return userOverQuota.value || props.history.isDeleted;
});
</script>

<template>
    <div v-if="hasMessages" class="mx-3 my-2">
        <BAlert :show="history.isDeleted" variant="warning">
            {{ localize("This history has been deleted") }}
        </BAlert>

        <BAlert :show="userOverQuota" variant="warning">
            {{
                localize(
                    "You are over your disk quota. Tool execution is on hold until your disk usage drops below your allocated quota."
                )
            }}
        </BAlert>
    </div>
</template>

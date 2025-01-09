<script setup lang="ts">
import { BAlert } from "bootstrap-vue";

import localize from "@/utils/localization";
import { orList } from "@/utils/strings";

import HelpText from "@/components/Help/HelpText.vue";

interface Props {
    extensions?: string[];
}

defineProps<Props>();
</script>

<template>
    <div class="d-flex align-items-center justify-content-between">
        <BAlert v-if="extensions?.length" class="w-100 py-0" variant="secondary" show>
            <HelpText
                uri="galaxy.collections.collectionBuilder.filteredExtensions"
                :text="localize('Filtered extensions: ')" />
            <strong>{{ orList(extensions) }}</strong>
        </BAlert>
    </div>
</template>

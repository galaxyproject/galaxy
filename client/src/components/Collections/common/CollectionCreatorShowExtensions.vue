<script setup lang="ts">
import { BAlert } from "bootstrap-vue";

import localize from "@/utils/localization";
import { orList } from "@/utils/strings";

import HelpText from "@/components/Help/HelpText.vue";

interface Props {
    extensions?: string[];
    upload?: boolean;
}

defineProps<Props>();
</script>

<template>
    <div class="d-flex align-items-center justify-content-between mt-2">
        <BAlert
            v-if="extensions?.length"
            class="w-100 py-0 d-flex justify-content-between flex-gapx-1"
            variant="secondary"
            show>
            <div>
                <HelpText
                    :uri="`galaxy.collections.collectionBuilder.${
                        upload ? 'requiredUploadExtensions' : 'filteredExtensions'
                    }`"
                    :text="localize(`${upload ? 'Required' : 'Filtered'} format(s):`)" />
                <strong>{{ orList(extensions) }}</strong>
            </div>
            <HelpText uri="galaxy.datasets.formatVsDatatypeVsExtension" :text="localize('format?')" />
        </BAlert>
    </div>
</template>

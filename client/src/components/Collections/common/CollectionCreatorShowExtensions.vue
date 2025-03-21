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
                    :text="localize(`${upload ? '必需' : '筛选'}格式：`)" />
                <strong>{{ orList(extensions) }}</strong>
            </div>
            <strong>
                <i>
                    <HelpText uri="galaxy.datasets.formatVsDatatypeVsExtension" :text="localize('格式？')" />
                </i>
            </strong>
        </BAlert>
    </div>
</template>

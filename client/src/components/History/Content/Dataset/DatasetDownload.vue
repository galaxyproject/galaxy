<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faSave } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, BDropdown, BDropdownItem } from "bootstrap-vue";
import { computed } from "vue";

import { type HDADetailed } from "@/api";
import { prependPath } from "@/utils/redirect";

library.add(faSave);

interface Props {
    item: HDADetailed;
}

const props = defineProps<Props>();

const emit = defineEmits(["on-download"]);

const metaFiles = computed(() => {
    return props.item.meta_files;
});
const hasMetaFiles = computed(() => {
    return metaFiles.value && metaFiles.value.length > 0;
});
const metaDownloadUrl = computed(() => {
    return prependPath(`api/datasets/${props.item.id}/metadata_file?metadata_file=`);
});
const downloadUrl = computed(() => {
    return prependPath(`api/datasets/${props.item.id}/display?to_ext=${props.item.extension}`);
});

function onDownload(resource: string, extension = "") {
    emit("on-download", `${resource}${extension}`);
}
</script>

<template>
    <BDropdown
        v-if="hasMetaFiles"
        v-b-tooltip.hover
        dropup
        no-caret
        no-flip
        size="sm"
        variant="link"
        toggle-class="text-decoration-none"
        title="Download"
        class="download-btn"
        data-description="dataset download">
        <template v-slot:button-content>
            <FontAwesomeIcon :icon="faSave" />
        </template>

        <BDropdownItem v-localize :href="downloadUrl" @click.prevent.stop="onDownload(downloadUrl)">
            Download Dataset
        </BDropdownItem>

        <BDropdownItem
            v-for="(metaFile, index) of metaFiles"
            :key="index"
            :data-description="`download ${metaFile.file_type}`"
            :href="metaDownloadUrl + metaFile.file_type"
            @click.prevent.stop="onDownload(metaDownloadUrl, metaFile.file_type)">
            Download {{ metaFile.file_type }}
        </BDropdownItem>
    </BDropdown>

    <BButton
        v-else
        v-b-tooltip.hover
        class="download-btn px-1"
        title="Download"
        size="sm"
        variant="link"
        :href="downloadUrl"
        @click.prevent.stop="onDownload(downloadUrl)">
        <FontAwesomeIcon :icon="faSave" />
    </BButton>
</template>

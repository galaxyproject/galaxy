<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faBug, faChartBar, faInfoCircle, faLink, faRedo, faSitemap } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";
import { computed } from "vue";

import { type HDADetailed } from "@/api";
import { copy as sendToClipboard } from "@/utils/clipboard";
import localize from "@/utils/localization";
import { absPath, prependPath } from "@/utils/redirect";

import { type ItemUrls } from ".";

import DatasetDownload from "@/components/History/Content/Dataset/DatasetDownload.vue";

library.add(faBug, faChartBar, faInfoCircle, faLink, faRedo, faSitemap);

interface Props {
    item: HDADetailed;
    writable: boolean;
    showHighlight: boolean;
    itemUrls: ItemUrls;
}

const props = withDefaults(defineProps<Props>(), {
    writable: true,
    showHighlight: false,
});

const emit = defineEmits(["toggleHighlights"]);

const showDownloads = computed(() => {
    return !props.item.purged && ["ok", "failed_metadata", "error"].includes(props.item.state);
});
const showError = computed(() => {
    return props.item.state === "error" || props.item.state === "failed_metadata";
});
const reportErrorUrl = computed(() => {
    return prependPath(props.itemUrls.reportError!);
});
const downloadUrl = computed(() => {
    return prependPath(`api/datasets/${props.item.id}/display?to_ext=${props.item.extension}`);
});

function onCopyLink() {
    const msg = localize("Link copied to your clipboard");
    sendToClipboard(absPath(downloadUrl.value), msg);
}

function onDownload(resource: string) {
    window.location.href = resource;
}

function onHighlight() {
    emit("toggleHighlights");
}

function onError() {
    window.location.href = reportErrorUrl.value;
}
</script>

<template>
    <div class="dataset-actions mb-1">
        <div class="clearfix">
            <div class="btn-group float-left">
                <BButton
                    v-if="showError"
                    v-b-tooltip.hover
                    class="px-1"
                    title="Error"
                    size="sm"
                    variant="link"
                    :href="reportErrorUrl"
                    @click.prevent.stop="onError">
                    <FontAwesomeIcon :icon="faBug" />
                </BButton>

                <DatasetDownload v-if="showDownloads" :item="item" @on-download="onDownload" />

                <BButton
                    v-if="showDownloads"
                    v-b-tooltip.hover
                    class="px-1"
                    title="Copy Link"
                    size="sm"
                    variant="link"
                    @click.stop="onCopyLink">
                    <FontAwesomeIcon :icon="faLink" />
                </BButton>

                <BButton
                    v-if="showHighlight"
                    v-b-tooltip.hover
                    class="highlight-btn px-1"
                    title="Show Related Items"
                    size="sm"
                    variant="link"
                    @click.stop="onHighlight">
                    <FontAwesomeIcon :icon="faSitemap" />
                </BButton>
            </div>
        </div>
    </div>
</template>

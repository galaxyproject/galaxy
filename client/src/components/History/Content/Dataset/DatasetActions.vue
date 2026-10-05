<script setup lang="ts">
import { faBug, faChartBar, faInfoCircle, faKey, faLink, faRedo, faSitemap } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { storeToRefs } from "pinia";
import { computed } from "vue";
import { useRouter } from "vue-router";

import type { HDADetailed } from "@/api";
import { useConfig } from "@/composables/config";
import { useDatasetProtection } from "@/composables/datasetProtection";
import { useUserStore } from "@/stores/userStore";
import { copy as sendToClipboard } from "@/utils/clipboard";
import localize from "@/utils/localization";
import { absPath, prependPath } from "@/utils/redirect";

import type { ItemUrls } from ".";

import GButton from "@/components/BaseComponents/GButton.vue";
import DatasetDownload from "@/components/History/Content/Dataset/DatasetDownload.vue";

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

const router = useRouter();

const showDownloads = computed(() => {
    return !props.item.purged && ["ok", "failed_metadata", "error"].includes(props.item.state);
});
const showError = computed(() => {
    return props.item.state === "error" || props.item.state === "failed_metadata";
});
const showInfo = computed(() => {
    return props.item.accessible;
});
const showVisualizations = computed(() => {
    return !props.item.purged && ["ok", "failed_metadata", "error"].includes(props.item.state);
});
const showRerun = computed(() => {
    return props.item.accessible && props.item.rerunnable && props.item.creating_job && props.item.state != "upload";
});

const { config } = useConfig(true);
const { isAnonymous } = storeToRefs(useUserStore());

const isCrypt4gh = computed(() => {
    const ext = props.item.extension;
    return Boolean(config.value?.crypt4gh_enabled) && (ext === "c4gh" || Boolean(ext?.endsWith(".c4gh")));
});
const datasetId = computed(() => props.item.id);
const { status: protectionStatus, authorizing, authorize } = useDatasetProtection(datasetId, isCrypt4gh);
const showAuthorizeCompute = computed(() => {
    return isCrypt4gh.value && !isAnonymous.value && !props.item.purged && props.item.state === "ok";
});
const authorizeComputeTitle = computed(() => {
    if (authorizing.value) {
        return localize("Authorizing...");
    }
    const expiresAt = protectionStatus.value?.ready ? protectionStatus.value.expires_at : null;
    if (expiresAt) {
        return `${localize("Authorized for your jobs until")} ${new Date(`${expiresAt}Z`).toLocaleString()}. ${localize("Click to renew.")}`;
    }
    return localize("Authorize your jobs to decrypt this dataset");
});

const reportErrorUrl = computed(() => {
    return prependPath(props.itemUrls.reportError!);
});
const showDetailsUrl = computed(() => {
    return prependPath(props.itemUrls.showDetails!);
});
const visualizeUrl = computed(() => {
    return prependPath(props.itemUrls.visualize!);
});
const rerunUrl = computed(() => {
    return prependPath(props.itemUrls.rerun!);
});
const downloadUrl = computed(() => {
    return prependPath(`api/datasets/${props.item.id}/download?to_ext=${props.item.extension}`);
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
    router.push(`/datasets/${props.item.id}/error`);
}

function onInfo() {
    router.push(`/datasets/${props.item.id}/details`);
}

function onVisualize() {
    router.push(`/datasets/${props.item.id}/visualize`);
}

function onRerun() {
    router.push(`/?job_id=${props.item.creating_job}`);
}

function onAuthorizeCompute() {
    authorize((props.item as Record<string, unknown>)["metadata_crypt4gh_header"] as string | undefined);
}
</script>

<template>
    <div class="dataset-actions mb-1">
        <div class="clearfix">
            <div class="btn-group float-left">
                <GButton
                    v-if="showError"
                    v-g-tooltip.hover
                    class="px-1"
                    title="Error"
                    size="small"
                    transparent
                    :href="reportErrorUrl"
                    @click.prevent.stop="onError">
                    <FontAwesomeIcon :icon="faBug" />
                </GButton>

                <DatasetDownload v-if="showDownloads" :item="item" @on-download="onDownload" />

                <GButton
                    v-if="showDownloads"
                    v-g-tooltip.hover
                    class="px-1"
                    title="Copy Link"
                    size="small"
                    transparent
                    @click.stop="onCopyLink">
                    <FontAwesomeIcon :icon="faLink" />
                </GButton>

                <GButton
                    v-if="showInfo"
                    v-g-tooltip.hover
                    class="info-btn px-1"
                    title="Dataset Details"
                    size="small"
                    transparent
                    :href="showDetailsUrl"
                    @click.prevent.stop="onInfo">
                    <FontAwesomeIcon :icon="faInfoCircle" />
                </GButton>

                <GButton
                    v-if="showVisualizations"
                    v-g-tooltip.hover
                    class="visualize-btn px-1"
                    title="Visualize"
                    size="small"
                    transparent
                    :href="visualizeUrl"
                    @click.prevent.stop="onVisualize">
                    <FontAwesomeIcon :icon="faChartBar" />
                </GButton>

                <GButton
                    v-if="showHighlight"
                    v-g-tooltip.hover
                    class="highlight-btn px-1"
                    title="Show Related Items"
                    size="small"
                    transparent
                    @click.stop="onHighlight">
                    <FontAwesomeIcon :icon="faSitemap" />
                </GButton>

                <GButton
                    v-if="writable && showRerun"
                    v-g-tooltip.hover
                    class="rerun-btn px-1"
                    title="Run Job Again"
                    size="small"
                    transparent
                    :href="rerunUrl"
                    @click.prevent.stop="onRerun">
                    <FontAwesomeIcon :icon="faRedo" />
                </GButton>

                <GButton
                    v-if="showAuthorizeCompute"
                    v-g-tooltip.hover
                    class="authorize-compute-btn px-1"
                    :class="{ 'text-success': protectionStatus?.ready }"
                    :title="authorizeComputeTitle"
                    size="small"
                    transparent
                    :disabled="authorizing"
                    @click.prevent.stop="onAuthorizeCompute">
                    <FontAwesomeIcon :icon="faKey" />
                </GButton>
            </div>
        </div>
    </div>
</template>

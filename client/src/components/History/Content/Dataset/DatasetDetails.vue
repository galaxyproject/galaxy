<script setup lang="ts">
import { BLink } from "bootstrap-vue";
import { computed } from "vue";

import { hasDetails } from "@/api";
import { STATES } from "@/components/History/Content/model/states";
import { useDatasetStore } from "@/stores/datasetStore";

import type { ItemUrls } from ".";

import DatasetActions from "./DatasetActions.vue";
import DatasetMiscInfo from "./DatasetMiscInfo.vue";

const datasetStore = useDatasetStore();

interface Props {
    id: string;
    writable?: boolean;
    showHighlight?: boolean;
    itemUrls: ItemUrls;
}

const props = withDefaults(defineProps<Props>(), {
    writable: true,
    showHighlight: false,
});

const emit = defineEmits<{
    (e: "toggleHighlights"): void;
    (e: "edit"): void;
}>();

const result = computed(() => datasetStore.getDataset(props.id));
const isLoading = computed(() => datasetStore.isLoadingDataset(props.id));

const stateText = computed(() => result.value && STATES[result.value.state] && STATES[result.value.state].text);

function toggleHighlights() {
    emit("toggleHighlights");
}
</script>

<template>
    <div>
        <div v-if="result && !isLoading && hasDetails(result)" class="dataset">
            <div class="details not-loading">
                <div class="summary">
                    <div v-if="stateText" class="mb-1">{{ stateText }}</div>
                    <div v-else-if="result.misc_blurb" class="blurb">
                        <span class="value">{{ result.misc_blurb }}</span>
                    </div>
                    <span v-if="result.file_ext" class="datatype">
                        <label v-localize class="prompt">format</label>
                        <span class="value">{{ result.file_ext }}</span>
                    </span>
                    <span v-if="result.genome_build" class="dbkey">
                        <label v-localize class="prompt">database</label>
                        <BLink class="value" data-label="Database/Build" @click.stop="$emit('edit')">{{
                            result.genome_build
                        }}</BLink>
                    </span>
                    <DatasetMiscInfo v-if="result.misc_info" :misc-info="result.misc_info" />
                </div>
                <DatasetActions
                    :item="result"
                    :writable="writable"
                    :show-highlight="showHighlight"
                    :item-urls="itemUrls"
                    @toggleHighlights="toggleHighlights" />
                <pre v-if="result.peek" class="dataset-peek p-1" v-html="result.peek" />
            </div>
        </div>
        <div v-else class="dataset">
            <!--
                placeholder skeleton for loading smoothly without a spinner
                (which you don't even see since this happens pretty fast, but it
                should be pretty accurate -- longer term it might be worth
                having more standard 'placeholder' versions of pre-loaded
                components) )
            -->
            <div class="p-2 details loading">
                <div class="summary">
                    <div class="blurb">
                        <span class="value">? lines</span>
                    </div>
                    <span class="datatype">
                        <label v-localize class="prompt">format</label>
                        <span class="value">...</span>
                    </span>
                    <span class="dbkey">
                        <label v-localize class="prompt">database</label>
                        <span class="value">?</span>
                    </span>
                    <div class="info">
                        <span class="value">Loading</span>
                    </div>
                </div>
                <div class="dataset-actions mb-1">
                    <div class="clearfix">
                        <div class="btn-group float-left">
                            <button disabled class="btn px-1 btn-link btn-sm">
                                <span class="fa fa-save"></span>
                            </button>
                            <button disabled class="btn px-1 btn-link btn-sm">
                                <span class="fa fa-link"></span>
                            </button>
                            <button disabled class="btn px-1 btn-link btn-sm">
                                <span class="fa fa-info-circle"></span>
                            </button>
                            <button disabled class="btn px-1 btn-link btn-sm">
                                <span class="fa fa-bar-chart-o"></span>
                            </button>
                            <button disabled class="btn px-1 btn-link btn-sm">
                                <span class="fa fa-sitemap"></span>
                            </button>
                        </div>
                    </div>
                </div>
                <!-- this looks a mess, but whitespace pads the pre and makes it look wonky -->
                <pre
                    class="dataset-peek p-1"><table cellspacing="0" cellpadding="3"><tbody><tr><td>Dataset peek loading...</td></tr></tbody></table></pre>
            </div>
        </div>
    </div>
</template>

<style scoped>
.details .summary div.info {
    max-height: 4rem;
    overflow-y: auto;
}
</style>

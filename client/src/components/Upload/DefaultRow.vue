<script setup>
import { computed } from "vue";
import Popper from "@/components/Popper/Popper.vue";
import Select2 from "@/components/Select2";
import { bytesToString } from "utils/utils";

const props = defineProps({
    listGenomes: Array,
    listExtensions: Array,
    extensions: Array,
    extension: String,
    genome: String,
    model: Object,
    index: String,
});
const id = computed(() => props.model.id);
const percentage = computed(() => parseInt(props.model.percentage || 0));
const extensionDetails = computed(() => props.extensions.find((item) => item.id === props.extension));

/** Dictionary of upload states and associated icons */
const status_classes = {
    init: "upload-icon-button fa fa-trash-o",
    queued: "upload-icon fa fa-spinner fa-spin",
    running: "upload-icon fa fa-spinner fa-spin",
    success: "upload-icon-button fa fa-check",
    error: "upload-icon-button fa fa-exclamation-triangle",
};

function inputPaste() {
    props.model.file_size = props.model.file_content.length;
}
</script>

<template>
    <div :id="`upload-row-${id}`" class="upload-row p-2" :class="{ 'bg-light': index % 2 === 0 }">
        <div class="d-flex justify-content-around">
            <div class="upload-text-column">
                <div v-if="model.file_mode == 'new'" class="upload-mode upload-mode-text fa fa-edit" />
                <div v-if="model.file_mode == 'local'" class="upload-mode fa fa-laptop" />
                <div v-if="model.file_mode == 'ftp'" class="upload-mode fa fa-folder-open-o" />
                <b-input v-model="model.file_name" class="upload-title ml-2 border rounded" />
            </div>
            <div class="upload-size">
                {{ bytesToString(model.file_size) }}
            </div>
            <div>
                <span class="upload-extension float-left mr-3">
                    <select2 v-model="model.extension">
                        <option v-for="(ext, index) in extensions" :key="index" :value="ext.id">{{ ext.text }}</option>
                    </select2>
                </span>
            </div>
            <Popper reference-is="span" popper-is="span" placement="bottom">
                <template v-slot:reference>
                    <span class="upload-extension-info upload-icon-button fa fa-search" />
                </template>
                <div class="p-3">
                    <div v-if="extensionDetails.description">
                        {{ extensionDetails.description }}
                        <div v-if="extensionDetails.description_url">
                            &nbsp;(<a :href="extensionDetails.description_url" target="_blank">read more</a>)
                        </div>
                    </div>
                    <div v-else>There is no description available for this file extension.</div>
                </div>
            </Popper>
            <div class="upload-genome">
                <select2 v-model="model.genome">
                    <option v-for="(listGenome, index) in listGenomes" :key="index" :value="listGenome.id">
                        {{ listGenome.text }}
                    </option>
                </select2>
            </div>
            <div class="upload-settings upload-icon-button fa fa-gear" />
            <div class="upload-info">
                <div class="upload-info-text" />
                <div class="upload-info-progress progress">
                    <div
                        class="upload-progress-bar progress-bar progress-bar-success"
                        :style="{ width: `${percentage}%` }" />
                    <div class="upload-percentage">
                        <div v-if="percentage !== 100">{{ percentage }}%</div>
                        <div v-else>Adding to history...</div>
                    </div>
                </div>
            </div>
            <div class="upload-symbol" :class="status_classes.init" />
        </div>
        <div v-if="model.file_mode == 'new'" class="upload-text">
            <div class="upload-text-info">
                Download data from the web by entering URLs (one per line) or directly paste content.
            </div>
            <textarea v-model="model.file_content" class="upload-text-content form-control" @input="inputPaste" />
        </div>
    </div>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";
.upload-text-content {
    width: 100%;
    height: 80px;
    background: inherit;
    color: $text-color;
    white-space: pre;
    overflow: auto;
}
</style>

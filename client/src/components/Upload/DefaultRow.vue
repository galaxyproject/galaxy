<script setup>
import { computed } from "vue";
import Popper from "@/components/Popper/Popper.vue";
import Select2 from "@/components/Select2";
import UploadSettings from "./UploadSettings";
import { bytesToString } from "utils/utils";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faEdit, faLaptop, faFolderOpen, faSearch } from "@fortawesome/free-solid-svg-icons";

library.add(faEdit, faLaptop, faFolderOpen, faSearch);

const props = defineProps({
    listGenomes: Array,
    listExtensions: Array,
    extensions: Array,
    extension: String,
    genome: String,
    model: Object,
    index: Number,
});
const id = computed(() => props.model.id);
const percentage = computed(() => parseInt(props.model.percentage || 0));
const extensionDetails = computed(() => props.extensions.find((item) => item.id === props.model.extension));

/** Dictionary of upload states and associated icons */
const status_classes = {
    init: "cursor-pointer fa fa-trash-o",
    queued: "fa fa-spinner fa-spin",
    running: "fa fa-spinner fa-spin",
    success: "cursor-pointer fa fa-check",
    error: "cursor-pointer fa fa-exclamation-triangle",
};

function inputPaste() {
    props.model.file_size = props.model.file_content.length;
}

function removeUpload() {
    if (["init", "success", "error"].indexOf(this.model.status) !== -1) {
        //this.app.collection.remove(this.model);
    }
}
</script>

<template>
    <div :id="`upload-row-${id}`" class="upload-row p-2" :class="{ 'bg-light': index % 2 === 0 }">
        <div class="d-flex justify-content-around">
            <div>
                <FontAwesomeIcon v-if="model.file_mode == 'new'" icon="fa-edit" />
                <FontAwesomeIcon v-if="model.file_mode == 'local'" icon="fa-laptop" />
                <FontAwesomeIcon v-if="model.file_mode == 'ftp'" icon="fa-folder-open" />
            </div>
            <b-input v-model="model.file_name" class="upload-title ml-2 border rounded" />
            <div class="upload-size">
                {{ bytesToString(model.file_size) }}
            </div>
            <select2 class="upload-extension" v-model="model.extension">
                <option v-for="(ext, index) in extensions" :key="index" :value="ext.id">{{ ext.text }}</option>
            </select2>
            <Popper reference-is="span" popper-is="span" placement="bottom" mode="light">
                <template v-slot:reference>
                    <FontAwesomeIcon icon="fa-search" />
                </template>
                <div class="p-2">
                    <div v-if="extensionDetails && extensionDetails.description">
                        {{ extensionDetails.description }}
                        <span v-if="extensionDetails.description_url">
                            &nbsp;(<a :href="extensionDetails.description_url" target="_blank">read more</a>)
                        </span>
                    </div>
                    <div v-else>There is no description available for this file extension.</div>
                </div>
            </Popper>
            <select2 v-model="model.genome" class="upload-genome">
                <option v-for="(listGenome, index) in listGenomes" :key="index" :value="listGenome.id">
                    {{ listGenome.text }}
                </option>
            </select2>
            <div>
                <UploadSettings :model="model" />
            </div>
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
            <div>
                <div class="upload-symbol" :class="model.status || status_classes.init" @click="removeUpload" />
            </div>
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

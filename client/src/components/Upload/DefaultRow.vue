<script setup>
import { computed, ref } from "vue";
import Popper from "@/components/Popper/Popper.vue";
import Select2 from "@/components/Select2";
import UploadExtensionDetails from "./UploadExtensionDetails";
import UploadSettings from "./UploadSettings";
import { bytesToString } from "utils/utils";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faEdit, faLaptop, faFolderOpen } from "@fortawesome/free-solid-svg-icons";

library.add(faEdit, faLaptop, faFolderOpen);

const props = defineProps({
    listGenomes: Array,
    listExtensions: Array,
    extensions: Array,
    extension: String,
    genome: String,
    model: Object,
    index: Number,
    percentage: Number,
    fileMode: String,
    status: String,
});

const emit = defineEmits();

const fileContent = ref("");

const percentageInt = computed(() => parseInt(props.percentage || 0));
const extensionDetails = computed(() => props.extensions.find((ext) => ext.id === props.model.extension) || {});
const extensionDescription = computed(() => extensionDetails.value.description);
const extensionDescriptionUrl = computed(() => extensionDetails.value.description_url);
const removeIcon = computed(() => status_classes[props.status] || status_classes.init);

/** Dictionary of upload states and associated icons */
const status_classes = {
    init: "cursor-pointer fa fa-trash-o",
    queued: "fa fa-spinner fa-spin",
    running: "fa fa-spinner fa-spin",
    success: "cursor-pointer fa fa-check",
    error: "cursor-pointer fa fa-exclamation-triangle",
};

function inputFileContent() {
    emit("input", props.index, { file_content: fileContent.value, file_size: fileContent.value.length });
}

function removeUpload() {
    if (["init", "success", "error"].indexOf(props.status) !== -1) {
        emit("remove", props.index);
    }
}
</script>

<template>
    <div :id="`upload-row-${index}`" class="upload-row p-2" :class="{ 'bg-light': index % 2 === 0 }">
        <div class="d-flex justify-content-around">
            <div>
                <FontAwesomeIcon v-if="fileMode == 'new'" icon="fa-edit" />
                <FontAwesomeIcon v-if="fileMode == 'local'" icon="fa-laptop" />
                <FontAwesomeIcon v-if="fileMode == 'ftp'" icon="fa-folder-open" />
            </div>
            <b-input v-model="model.file_name" class="upload-title ml-2 border rounded" />
            <div class="upload-size">
                {{ bytesToString(model.file_size) }}
            </div>
            <select2 class="upload-extension" v-model="model.extension">
                <option v-for="(ext, index) in extensions" :key="index" :value="ext.id">{{ ext.text }}</option>
            </select2>
            <div>
                <UploadExtensionDetails
                    :description="extensionDescription"
                    :description-url="extensionDescriptionUrl" />
            </div>
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
                        :style="{ width: `${percentageInt}%` }" />
                    <div class="upload-percentage">{{ percentageInt }}%</div>
                </div>
            </div>
            <div>
                <div class="upload-symbol" :class="removeIcon" @click="removeUpload" />
            </div>
        </div>
        <div v-if="fileMode == 'new'" class="upload-text">
            <div class="upload-text-info">
                Download data from the web by entering URLs (one per line) or directly paste content.
            </div>
            <textarea v-model="fileContent" class="upload-text-content form-control" @input="inputFileContent" />
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

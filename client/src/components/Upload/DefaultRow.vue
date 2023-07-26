<script setup>
import { computed } from "vue";

const props = defineProps({
    listGenomes: Array,
    listExtensions: Array,
    extensions: Array,
    extension: String,
    genome: String,
    model: Object,
});
const id = computed(() => model.id);

/** Dictionary of upload states and associated icons */
const status_classes = {
    init: "upload-icon-button fa fa-trash-o",
    queued: "upload-icon fa fa-spinner fa-spin",
    running: "upload-icon fa fa-spinner fa-spin",
    success: "upload-icon-button fa fa-check",
    error: "upload-icon-button fa fa-exclamation-triangle",
};
</script>

<template>
    <tr id="upload-row-${id}" class="upload-row">
        <td>
            <div class="upload-text-column">
                <div class="upload-mode" />
                <input class="upload-title ml-2 border rounded" />
                <div class="upload-text">
                    <div class="upload-text-info">
                        Download data from the web by entering URLs (one per line) or directly paste content.
                    </div>
                    <textarea class="upload-text-content form-control" />
                </div>
            </div>
        </td>
        <td>
            <div class="upload-size" />
        </td>
        <td>
            <div class="upload-extension float-left mr-1" />
            <div class="upload-extension-info upload-icon-button fa fa-search" />
        </td>
        <td>
            <div class="upload-genome" />
        </td>
        <td>
            <div class="upload-settings upload-icon-button fa fa-gear" />
        </td>
        <td>
            <div class="upload-info">
                <div class="upload-info-text" />
                <div class="upload-info-progress progress">
                    <div class="upload-progress-bar progress-bar progress-bar-success" />
                    <div class="upload-percentage">0%</div>
                </div>
            </div>
        </td>
        <td>
            <div class="upload-symbol ${status_classes.init}" />
        </td>
    </tr>
</template>

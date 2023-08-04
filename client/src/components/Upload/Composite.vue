<script setup>
import { submitUpload } from "utils/uploadbox";
import { computed, ref } from "vue";

import UploadSettingsSelect from "./UploadSettingsSelect.vue";

const props = defineProps({
    effectiveExtensions: {
        type: Array,
        required: true,
    },
    hasCallback: {
        type: Boolean,
        default: false,
    },
    listGenomes: {
        type: Array,
        required: true,
    },
    details: {
        type: Object,
        required: true,
    },
});

const extension = ref("_select_");
const genome = ref(props.details.defaultDbKey);
const uploadItems = ref({});

const listExtensions = computed(() => {
    const result = props.effectiveExtensions.filter((ext) => ext.composite_files);
    result.unshift({ id: "_select_", text: "Select" });
    return result;
});

const running = computed(() => {
    const model = uploadKeys.value[0];
    return model && model.status === "running";
});

const readyStart = computed(() => {
    const readyStates = uploadValues.value.filter((v) => v.status === "ready").length;
    const optionalStates = uploadValues.value.filter((v) => v.optional === true).length;
    return readyStates + optionalStates == uploadValues.value.length && uploadValues.value.length > 0;
});

const showHelper = computed(() => uploadKeys.value.length === 0);

const uploadValues = computed(() => Object.values(uploadItems.value));
const uploadKeys = computed(() => Object.keys(uploadItems.value));

/** Builds the basic ui with placeholder rows for each composite data type file */
function eventAnnounce(model) {
    /*var upload_row = new UploadRow(this, { model: model });
    this.$uploadTable().find("tbody:first").append(upload_row.$el);
    this.showHelper = this.collection.length == 0;
    upload_row.render();*/
}

/** Refresh error state */
function eventError(info) {
    UploadValues.value.forEach((model) => {
        model.info = info;
        model.status = "error";
    });
}

/** Refresh progress state */
function eventProgress(percentage) {
    UploadValues.value.forEach((model) => {
        model.percentage = percentage;
    });
}

/** Remove all */
function eventReset() {
    if (UploadValues.value.filter((v) => v.status === "running").length > 0) {
        uploadItems.value = {};
        extension.value = props.details.defaultExtension;
        genome.value = props.details.defaultDbKey;
    }
}

/** Start upload process */
function eventStart() {
    uploadItems.value.forEach((model) => {
        model.genome = genome.value;
        model.extension = extension.value;
    });
    submitUpload({
        //url: props.details.uploadPath,
        //data: uploadModelsToPayload(this.collection.filter(), this.history_id, true),
        error: eventError(message),
        progress: eventProgress(percentage),
        success: eventSuccess,
    });
}

/** Refresh success state */
function eventSuccess() {
    UploadValues.value.forEach((model) => {
        model.status = "success";
    });
}

function inputExtension(newExtension) {
    uploadItems.value = {};
    let uploadCount = 0;
    const extensionDetails = listExtensions.value.find((v) => v.id === newExtension);
    if (extensionDetails && extensionDetails.composite_files) {
        extensionDetails.composite_files.forEach((item) => {
            const newUploadId = String(uploadCount++);
            uploadItems.value[newUploadId] = {
                id: newUploadId,
                file_desc: item.description || item.name,
                optional: item.optional,
            };
        });
    }
}

function inputDbkey(newDbkey) {
    genome.value = newDbkey;
}
</script>

<template>
    <div class="upload-view-composite">
        <div class="upload-box" :style="{ height: '335px' }">
            <div v-show="showHelper" class="upload-helper">Select a composite type</div>
            <table v-show="!showHelper" ref="uploadTable" class="upload-table ui-table-striped">
                <thead>
                    <tr>
                        <th />
                        <th />
                        <th>Description</th>
                        <th>Name</th>
                        <th>Size</th>
                        <th>Settings</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody />
            </table>
        </div>
        <div class="upload-footer">
            <span class="upload-footer-title">Composite Type:</span>
            <UploadSettingsSelect
                :value="extension"
                :options="listExtensions"
                :disabled="running"
                @input="inputExtension" />
            <span ref="footerExtensionInfo" class="upload-footer-extension-info upload-icon-button fa fa-search" />
            <span class="upload-footer-title">Genome/Build:</span>
            <UploadSettingsSelect :value="genome" :options="listGenomes" :disabled="running" @input="inputDbkey" />
        </div>
        <div class="upload-buttons">
            <b-button ref="btnClose" class="ui-button-default" title="Close" @click="$emit('dismiss')">
                <span v-if="hasCallback" v-localize>Close</span>
                <span v-else v-localize>Cancel</span>
            </b-button>
            <b-button
                id="btn-start"
                ref="btnStart"
                class="ui-button-default"
                :disabled="!readyStart"
                title="Start"
                :variant="readyStart ? 'primary' : ''"
                @click="eventStart">
                <span v-localize>Start</span>
            </b-button>
            <b-button id="btn-reset" ref="btnReset" class="ui-button-default" title="Reset" @click="eventReset">
                <span v-localize>Reset</span>
            </b-button>
        </div>
    </div>
</template>

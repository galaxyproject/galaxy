<script setup>
import { refreshContentsWrapper } from "utils/data";
import { submitUpload } from "utils/uploadbox";
import { computed, ref } from "vue";

import { uploadModelsToPayload } from "./helpers";
import UploadModel from "./upload-model";

import UploadSettingsSelect from "./UploadSettingsSelect.vue";

const props = defineProps({
    hasCallback: {
        type: Boolean,
        default: false,
    },
    details: {
        type: Object,
        required: true,
    },
});

const extension = ref("_select_");
const genome = ref(props.details.defaultDbKey);
const listExtensions = ref([]);
const listGenomes = ref([]);
const uploadItems = ref({});

const extensions = computed(() => {
    return [];
    const result = listExtensions.value.filter((ext) => ext.composite_files);
    result.unshift({ id: "_select_", text: "Select" });
    return result;
});

const running = computed(() => {
    /*var model = this.collection.first();
    if (model && model.get("status") == "running") {
        this.running = true;
    } else {
        this.running = false;
    }*/
    return true;
});
const readyStart = computed(() => {
    return true;
    /*const readyStates = this.collection.where({ status: "ready" }).length;
    const optionalStates = this.collection.where({ optional: true }).length;
    return readyStates + optionalStates == this.collection.length && this.collection.length > 0;*/
});
const showHelper = computed(() => Object.keys(uploadItems.value).length === 0);

function changeType(newType) {
    uploadItems.value = {};
    /*const details = this.extensionDetails(value);
    if (details && details.composite_files) {
        _.each(details.composite_files, (item) => {
            this.collection.add({
                id: this.collection.size(),
                file_desc: item.description || item.name,
                optional: item.optional,
            });
        });
    }*/
}

/** Builds the basic ui with placeholder rows for each composite data type file */
function eventAnnounce(model) {
    /*var upload_row = new UploadRow(this, { model: model });
    this.$uploadTable().find("tbody:first").append(upload_row.$el);
    this.showHelper = this.collection.length == 0;
    upload_row.render();*/
}

/** Refresh error state */
function eventError(message) {
    /*this.collection.each((it) => {
        it.set({ status: "error", info: message });
    });*/
}

/** Refresh progress state */
function eventProgress(percentage) {
    /*this.collection.each((it) => {
        it.set("percentage", percentage);
    });*/
}

/** Remove all */
function eventReset() {
    /*if (this.collection.where({ status: "running" }).length == 0) {
        this.collection.reset();
        this.extension = this.details.defaultExtension;
        this.genome = this.details.defaultDbKey;
        this.renderNonReactiveComponents();
    }*/
}
/** Start upload process */
function eventStart() {
    this.collection.each((model) => {
        model.set({
            genome: this.genome,
            extension: this.extension,
        });
    });
    submitUpload({
        url: props.details.uploadPath,
        //data: uploadModelsToPayload(this.collection.filter(), this.history_id, true),
        success: (message) => {
            eventSuccess(message);
        },
        error: (message) => {
            eventError(message);
        },
        progress: (percentage) => {
            _eventProgress(percentage);
        },
    });
}

/** Refresh success state */
function eventSuccess(message) {
    /*this.collection.each((it) => {
        it.set("status", "success");
    });*/
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
            <UploadSettingsSelect :value="extension" :options="extensions" :disabled="running" />
            <span ref="footerExtensionInfo" class="upload-footer-extension-info upload-icon-button fa fa-search" />
            <span class="upload-footer-title">Genome/Build:</span>
            <UploadSettingsSelect :value="genome" :options="listGenomes" :disabled="running" />
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

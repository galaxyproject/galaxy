<script setup lang="ts">
import { faUpload } from "@fortawesome/free-solid-svg-icons";
import { BButton } from "bootstrap-vue";
import { onMounted, type Ref, ref, watch } from "vue";
import Vue from "vue";

import { useGlobalUploadModal } from "@/composables/globalUploadModal";
import { getAppRoot } from "@/onload/loadConfig";
import { errorMessageAsString } from "@/utils/simple-error";

import { Model } from "./model";
import { Services } from "./services";
import { UrlTracker } from "./utilities";

import DataDialogSearch from "@/components/SelectionDialog/DataDialogSearch.vue";
import DataDialogTable from "@/components/SelectionDialog/DataDialogTable.vue";
import SelectionDialog from "@/components/SelectionDialog/SelectionDialog.vue";

interface Props {
    allowUpload?: boolean;
    format?: string;
    modalStatic?: boolean;
    library?: boolean;
    multiple?: boolean;
    title?: string;
    history: string;
    callback: (results: Array<Record>) => void;
}

interface Record {
    id: string;
    isLeaf: boolean;
    url: string;
}

const props = withDefaults(defineProps<Props>(), {
    multiple: false,
    format: "download",
    library: true,
    modalStatic: false,
    allowUpload: true,
    title: "",
});

const emit = defineEmits<{
    (e: "onCancel"): void;
    (e: "onUpload"): void;
    (e: "onOk", results: Array<Record>): void;
}>();

const { openGlobalUploadModal } = useGlobalUploadModal();

const errorMessage = ref("");
const filter = ref("");
const items: Ref<Array<Record>> = ref([]);
const modalShow = ref(true);
const optionsShow = ref(true);
const undoShow = ref(false);
const hasValue = ref(false);

const services = new Services();
const model = new Model({ multiple: props.multiple, format: props.format });
let urlTracker = new UrlTracker(getHistoryUrl());

/** Returns the default url i.e. the url of the current history **/
function getHistoryUrl() {
    return `${getAppRoot()}api/histories/${props.history}/contents?deleted=false`;
}

/** Add highlighting for record variations, i.e. datasets vs. libraries/collections **/
function formatRows() {
    for (const item of items.value) {
        let _rowVariant = "active";
        if (item.isLeaf) {
            _rowVariant = model.exists(item.id) ? "success" : "default";
        }
        Vue.set(item, "_rowVariant", _rowVariant);
    }
}

/** Collects selected datasets in value array **/
function onClick(record: Record) {
    if (record.isLeaf) {
        model.add(record);
        hasValue.value = model.count() > 0;
        if (props.multiple) {
            formatRows();
        } else {
            onOk();
        }
    } else {
        load(record.url);
    }
}

/** Called when user decides to upload new data */
function onUpload() {
    const propsData = {
        multiple: props.multiple,
        format: props.format,
        callback: props.callback,
        modalShow: true,
        selectable: true,
    };
    openGlobalUploadModal(propsData);
    modalShow.value = false;
    emit("onUpload");
}

/** Called when selection is complete, values are formatted and parsed to external callback **/
function onOk() {
    const results = model.finalize();
    modalShow.value = false;
    props.callback(results);
    emit("onOk", results);
}

/** Called when the modal is hidden */
function onCancel() {
    modalShow.value = false;
    emit("onCancel");
}

/** On clicking folder name div: overloader for the @click.stop in DataDialogTable **/
function onLoad(record: Record) {
    load(record.url);
}

/** Performs server request to retrieve data records **/
function load(url: string = "") {
    url = urlTracker.getUrl(url);
    filter.value = "";
    optionsShow.value = false;
    undoShow.value = !urlTracker.atRoot();
    services
        .get(url)
        .then((items) => {
            if (props.library && urlTracker.atRoot()) {
                items.unshift({
                    label: "Data Libraries",
                    url: `${getAppRoot()}api/libraries`,
                });
            }
            items.value = items;
            formatRows();
            optionsShow.value = true;
        })
        .catch((error) => {
            errorMessage.value = errorMessageAsString(error);
        });
}

onMounted(() => {
    if (props.history) {
        load();
    }
});

watch(
    () => history,
    () => {
        urlTracker = new UrlTracker(getHistoryUrl());
        load();
    }
);
</script>

<template>
    <SelectionDialog
        :error-message="errorMessage"
        :options-show="optionsShow"
        :modal-show="modalShow"
        :hide-modal="onCancel"
        :undo-show="undoShow"
        :disable-ok="!hasValue"
        :multiple="multiple"
        @onBack="load()"
        @onOk="onOk">
        <template v-slot:search>
            <DataDialogSearch v-model="filter" />
        </template>
        <template v-slot:options>
            <DataDialogTable
                v-if="optionsShow"
                :items="items"
                :multiple="multiple"
                :filter="filter"
                @clicked="onClick"
                @open="onLoad" />
        </template>
        <template v-slot:buttons>
            <BButton v-if="allowUpload" size="sm" @click="onUpload">
                <Icon :icon="faUpload" />
                Upload
            </BButton>
        </template>
    </SelectionDialog>
</template>

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

import SelectionDialog from "@/components/SelectionDialog/SelectionDialog.vue";

interface Record {
    id: string;
    isLeaf: boolean;
    url: string;
}

interface Props {
    allowUpload?: boolean;
    callback?: (results: Array<Record>) => void;
    filterOkState?: boolean;
    filterByTypeIds?: string[];
    format?: string;
    library?: boolean;
    modalStatic?: boolean;
    multiple?: boolean;
    title?: string;
    history: string;
}

const props = withDefaults(defineProps<Props>(), {
    allowUpload: true,
    callback: () => {},
    filterOkState: false,
    filterByTypeIds: undefined,
    format: "download",
    library: true,
    modalStatic: false,
    multiple: false,
    title: "",
});

const emit = defineEmits<{
    (e: "onCancel"): void;
    (e: "onOk", results: Array<Record>): void;
    (e: "onUpload"): void;
}>();

const { openGlobalUploadModal } = useGlobalUploadModal();

const errorMessage = ref("");
const filter = ref("");
const items: Ref<Array<Record>> = ref([]);
const hasValue = ref(false);
const modalShow = ref(true);
const optionsShow = ref(true);
const undoShow = ref(false);

const services = new Services();
const model = new Model({ multiple: props.multiple, format: props.format });
let urlTracker = new UrlTracker(getHistoryUrl());

/** Specifies data columns to be shown in the dialog's table */
const fields = [
    {
        key: "label",
    },
    {
        key: "extension",
    },
    {
        key: "tags",
    },
    {
        key: "update_time",
    },
];

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

/** Returns the default url i.e. the url of the current history **/
function getHistoryUrl() {
    let queryString = "&q=deleted&qv=false";
    if (props.filterOkState) {
        queryString += "&q=state-eq&qv=ok";
    }
    if (props.filterByTypeIds && props.filterByTypeIds.length > 0) {
        queryString += `&q=type_id-in&qv=${props.filterByTypeIds.join(",")}`;
    }
    return `${getAppRoot()}api/histories/${props.history}/contents?v=dev${queryString}`;
}

/** Called when the modal is hidden */
function onCancel() {
    modalShow.value = false;
    emit("onCancel");
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

/** Called when selection is complete, values are formatted and parsed to external callback **/
function onOk() {
    const results = model.finalize();
    modalShow.value = false;
    props.callback(results);
    emit("onOk", results);
}

/** On clicking folder name div: overloader for the @click.stop in DataDialogTable **/
function onOpen(record: Record) {
    load(record.url);
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

/** Performs server request to retrieve data records **/
function load(url: string = "") {
    url = urlTracker.getUrl(url);
    filter.value = "";
    optionsShow.value = false;
    undoShow.value = !urlTracker.atRoot();
    services
        .get(url)
        .then((incoming) => {
            if (props.library && urlTracker.atRoot()) {
                incoming.unshift({
                    label: "Data Libraries",
                    url: `${getAppRoot()}api/libraries`,
                });
            }
            items.value = incoming;
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
        :disable-ok="!hasValue"
        :fields="fields"
        :items="items"
        :total-items="items.length"
        :modal-show="modalShow"
        :multiple="multiple"
        :options-show="optionsShow"
        :undo-show="undoShow"
        @onCancel="onCancel"
        @onClick="onClick"
        @onOk="onOk"
        @onOpen="onOpen"
        @onUndo="load()">
        <template v-slot:buttons>
            <BButton v-if="allowUpload" size="sm" @click="onUpload">
                <Icon :icon="faUpload" />
                Upload
            </BButton>
        </template>
    </SelectionDialog>
</template>

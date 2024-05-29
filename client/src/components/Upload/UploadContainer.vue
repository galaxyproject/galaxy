<script setup>
import { BAlert, BTab, BTabs } from "bootstrap-vue";
import { getDatatypesMapper } from "components/Datatypes";
import LoadingSpan from "components/LoadingSpan";
import {
    AUTO_EXTENSION,
    DEFAULT_DBKEY,
    DEFAULT_EXTENSION,
    getUploadDatatypes,
    getUploadDbKeys,
} from "components/Upload/utils";
import { storeToRefs } from "pinia";
import { computed, onMounted, ref } from "vue";

import { canMutateHistory } from "@/api";
import { useHistoryStore } from "@/stores/historyStore";
import { useUploadStore } from "@/stores/uploadStore";
import { uploadPayload } from "@/utils/upload-payload.js";

import CompositeBox from "./CompositeBox";
import DefaultBox from "./DefaultBox";
import RulesInput from "./RulesInput";

const props = defineProps({
    auto: {
        type: Object,
        default: () => AUTO_EXTENSION,
    },
    chunkUploadSize: {
        type: Number,
        default: 1024,
    },
    currentHistoryId: {
        type: String,
        required: true,
    },
    currentUserId: {
        type: String,
        default: "",
    },
    datatypesDisableAuto: {
        type: Boolean,
        default: false,
    },
    defaultDbKey: {
        type: String,
        default: DEFAULT_DBKEY,
    },
    defaultExtension: {
        type: String,
        default: DEFAULT_EXTENSION,
    },
    fileSourcesConfigured: {
        type: Boolean,
        default: false,
    },
    ftpUploadSite: {
        type: String,
        default: "",
    },
    formats: {
        type: Array,
        default: null,
    },
    // Return uploads when done if supplied.
    hasCallback: {
        type: Boolean,
        default: false,
    },
    // Restrict the forms to a single dataset upload if false
    multiple: {
        type: Boolean,
        default: true,
    },
});

const extensionsSet = ref(false);
const datatypesMapper = ref(null);
const datatypesMapperReady = ref(false);
const dbKeysSet = ref(false);
const listExtensions = ref([]);
const listDbKeys = ref([]);
const regular = ref(null);

const { percentage, status } = storeToRefs(useUploadStore());

const { currentHistory } = storeToRefs(useHistoryStore());

const effectiveExtensions = computed(() => {
    if (props.formats === null || !datatypesMapperReady.value) {
        return listExtensions.value;
    } else {
        const result = [];
        listExtensions.value.forEach((extension) => {
            if (extension && extension.id == "auto") {
                result.push(extension);
            } else if (datatypesMapper.value.isSubTypeOfAny(extension.id, props.formats)) {
                result.push(extension);
            }
        });
        return result;
    }
});

const hasCompositeExtension = computed(() =>
    effectiveExtensions.value.some((extension) => !!extension.composite_files)
);
const hasRegularExtension = computed(() => effectiveExtensions.value.some((extension) => !extension.composite_files));
const historyAvailable = computed(() => Boolean(props.currentHistoryId));
const ready = computed(
    () => dbKeysSet.value && extensionsSet.value && historyAvailable.value && datatypesMapperReady.value
);
const canUploadToHistory = computed(() => currentHistory.value && canMutateHistory(currentHistory.value));
const showCollection = computed(() => !props.formats && props.multiple);
const showComposite = computed(() => !props.formats || hasCompositeExtension);
const showRegular = computed(() => !props.formats || hasRegularExtension);
const showRules = computed(() => !props.formats || props.multiple);

function immediateUpload(files) {
    regular.value?.addFiles(files, true);
}

function toData(items, history_id, composite = false) {
    return uploadPayload(items, history_id, composite);
}

async function loadExtensions() {
    listExtensions.value = await getUploadDatatypes(props.datatypesDisableAuto, props.auto);
    extensionsSet.value = true;
}

async function loadDbKeys() {
    listDbKeys.value = await getUploadDbKeys(props.defaultDbKey);
    dbKeysSet.value = true;
}

async function loadMappers() {
    if (props.formats !== null) {
        datatypesMapper.value = await getDatatypesMapper();
    }
    datatypesMapperReady.value = true;
}

function progress(newPercentage, newStatus = null) {
    if (newPercentage !== null) {
        percentage.value = newPercentage;
    }
    if (newStatus !== null) {
        status.value = newStatus;
    }
}

onMounted(() => {
    loadExtensions();
    loadDbKeys();
    loadMappers();
});

defineExpose({
    immediateUpload,
    listDbKeys,
    listExtensions,
    toData,
});
</script>

<template>
    <BAlert v-if="!canUploadToHistory" variant="warning" show>
        <span v-localize>
            The current history is immutable and you cannot upload data to it. Please select a different history or
            create a new one.
        </span>
    </BAlert>
    <BTabs v-else-if="ready">
        <BTab v-if="showRegular" id="regular" title="Regular" button-id="tab-title-link-regular">
            <DefaultBox
                ref="regular"
                :chunk-upload-size="chunkUploadSize"
                :default-db-key="defaultDbKey"
                :default-extension="defaultExtension"
                :effective-extensions="effectiveExtensions"
                :file-sources-configured="fileSourcesConfigured"
                :ftp-upload-site="currentUserId && ftpUploadSite"
                :has-callback="hasCallback"
                :history-id="currentHistoryId"
                :list-db-keys="listDbKeys"
                :multiple="multiple"
                @progress="progress"
                v-on="$listeners" />
        </BTab>
        <BTab v-if="showComposite" id="composite" title="Composite" button-id="tab-title-link-composite">
            <CompositeBox
                :effective-extensions="effectiveExtensions"
                :default-db-key="defaultDbKey"
                :file-sources-configured="fileSourcesConfigured"
                :ftp-upload-site="currentUserId && ftpUploadSite"
                :has-callback="hasCallback"
                :history-id="currentHistoryId"
                :list-db-keys="listDbKeys"
                v-on="$listeners" />
        </BTab>
        <BTab v-if="showCollection" id="collection" title="Collection" button-id="tab-title-link-collection">
            <DefaultBox
                :chunk-upload-size="chunkUploadSize"
                :default-db-key="defaultDbKey"
                :default-extension="defaultExtension"
                :effective-extensions="effectiveExtensions"
                :file-sources-configured="fileSourcesConfigured"
                :ftp-upload-site="currentUserId && ftpUploadSite"
                :has-callback="hasCallback"
                :history-id="currentHistoryId"
                :is-collection="true"
                :list-db-keys="listDbKeys"
                v-on="$listeners" />
        </BTab>
        <BTab v-if="showRules" id="rule-based" title="Rule-based" button-id="tab-title-link-rule-based">
            <RulesInput
                :file-sources-configured="fileSourcesConfigured"
                :ftp-upload-site="currentUserId && ftpUploadSite"
                :has-callback="hasCallback"
                :history-id="currentHistoryId"
                v-on="$listeners" />
        </BTab>
    </BTabs>
    <div v-else>
        <LoadingSpan message="Loading required information from Galaxy server." />
    </div>
</template>

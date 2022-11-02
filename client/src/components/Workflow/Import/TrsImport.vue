<script setup>
import TrsTool from "./TrsTool";
import TrsUrlImport from "./TrsUrlImport";
import { Toast } from "composables/toast";
import { Services } from "../services";
import { getGalaxyInstance } from "app";
import { safePath } from "utils/redirect";
import { computed, ref, watch } from "vue";
import { redirectOnImport } from "../utils";
import LoadingSpan from "components/LoadingSpan";
import TrsServerSelection from "./TrsServerSelection";
import DebouncedInput from "components/DebouncedInput";

const props = defineProps({
    queryTrsServer: {
        type: String,
        default: null,
    },
    queryTrsId: {
        type: String,
        default: null,
    },
    queryTrsVersionId: {
        type: String,
        default: null,
    },
    queryTrsUrl: {
        type: String,
        default: null,
    },
    isRun: {
        type: Boolean,
        default: false,
    },
});

const trsTool = ref(null);
const loading = ref(false);
const importing = ref(false);
const trsSelection = ref(null);
const errorMessage = ref(null);
const toolId = ref(props.queryTrsId);
const isAnonymous = getGalaxyInstance().user?.isAnonymous();
const isAutoImport = ref(props.queryTrsVersionId && props.queryTrsServer && props.queryTrsId);

const toolIdTrimmed = computed(() => {
    return toolId.value?.trim() || null;
});
const hasErrorMessage = computed(() => {
    return errorMessage.value != null;
});

watch(toolIdTrimmed, () => {
    onToolId();
});

const services = new Services();

const onToolId = () => {
    trsTool.value = null;
    errorMessage.value = null;
    if (!trsSelection.value || !toolIdTrimmed.value) {
        return;
    }
    loading.value = true;
    services
        .getTrsTool(trsSelection.value.id, toolIdTrimmed.value)
        .then((tool) => {
            trsTool.value = tool;
            if (isAutoImport.value) {
                let versionField = "name";
                const version = trsTool.value.versions.find((version) => {
                    if (version.name === props.queryTrsVersionId) {
                        return true;
                    } else if (version.id === props.queryTrsVersionId) {
                        versionField = "id";
                        return true;
                    }
                });
                if (version) {
                    importVersion(trsSelection.value.id, trsTool.value.id, version[versionField], props.isRun);
                } else {
                    Toast.warning(`Specified version: ${props.queryTrsVersionId} doesn't exist`);
                    isAutoImport.value = false;
                }
            }
        })
        .catch((e) => {
            trsTool.value = null;
            errorMessage.value = e;
        })
        .finally(() => {
            loading.value = false;
        });
};

const onTrsSelection = (selection) => {
    trsSelection.value = selection;
    if (toolIdTrimmed.value) {
        onToolId();
    }
};

const onTrsSelectionError = (message) => {
    errorMessage.value = message;
};

const importVersion = (trsId, toolIdToImport, version = null, isRunFormRedirect = false) => {
    importing.value = true;
    errorMessage.value = null;
    services
        .importTrsTool(trsId, toolIdToImport, version)
        .then((response) => {
            redirectOnImport(safePath("/"), response, isRunFormRedirect);
        })
        .catch((e) => {
            errorMessage.value = e || "Import failed for an unknown reason.";
        })
        .finally(() => {
            importing.value = false;
        });
};

const importVersionFromUrl = (url, isRunFormRedirect = false) => {
    importing.value = true;
    errorMessage.value = null;
    services
        .importTrsToolFromUrl(url)
        .then((response) => {
            redirectOnImport(safePath("/"), response, isRunFormRedirect);
        })
        .catch((e) => {
            errorMessage.value = e || "Import failed for an unknown reason.";
        })
        .finally(() => {
            importing.value = false;
        });
};
</script>

<template>
    <div>
        <b-card v-if="!isAnonymous" title="GA4GH Tool Registry Server (TRS) Workflow Import">
            <div>
                <b>TRS Server:</b>
                <TrsServerSelection
                    :trs-selection="trsSelection"
                    :query-trs-server="props.queryTrsServer"
                    @onError="onTrsSelectionError"
                    @onTrsSelection="onTrsSelection" />
            </div>
            <b-alert v-if="isAutoImport && !hasErrorMessage" show variant="info">
                <LoadingSpan message="Loading your Workflow" />
            </b-alert>
            <div v-else>
                <div class="my-3">
                    <DebouncedInput v-slot="{ value, input }" v-model="toolId">
                        <b-form-group label="TRS ID:" label-class="font-weight-bold">
                            <b-form-input id="trs-id-input" :value="value" @input="input" />
                        </b-form-group>
                    </DebouncedInput>
                </div>
                <div>
                    <b-alert v-if="loading" show variant="info">
                        <LoadingSpan :message="`Loading ${toolIdTrimmed}, this may take a while - please be patient`" />
                    </b-alert>
                    <b-alert :show="hasErrorMessage" variant="danger">{{ errorMessage }}</b-alert>
                    <b-alert v-if="importing" show variant="info">
                        <LoadingSpan message="Importing workflow" />
                    </b-alert>
                </div>
                <TrsTool
                    v-if="trsTool"
                    :trs-tool="trsTool"
                    @onImport="importVersion(trsSelection.id, trsTool.id, $event)" />
            </div>
            <hr/>
            <div>
                <TrsUrlImport
                    :query-trs-url="props.queryTrsUrl"
                    @onImport="importVersionFromUrl($event)" />
            </div>
        </b-card>
        <b-alert v-else class="text-center my-2" show variant="danger">
            Anonymous user cannot import workflows, please register or log in
        </b-alert>
    </div>
</template>

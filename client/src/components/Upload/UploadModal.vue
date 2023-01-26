<script setup>
import UploadModalContent from "./UploadModalContent";

import { ref, watch } from "vue";
import { getAppRoot } from "onload";

import { useCurrentUser } from "composables/user";
import { useUserHistories } from "composables/userHistories";
import { useConfig } from "composables/config";
import { wait } from "@/utils/wait";

const { currentUser } = useCurrentUser();
const { currentHistoryId } = useUserHistories(currentUser);

const { config, isLoaded } = useConfig();

function getDefaultOptions() {
    const baseOptions = {
        title: "Upload from Disk or Web",
        modalStatic: true,
        callback: null,
        multiple: true,
        selectable: false,
        uploadPath: "",
        immediateUpload: false,
        immediateFiles: null,
    };

    const configOptions = isLoaded.value
        ? {
              uploadPath: config.value.nginx_upload_path ?? `${getAppRoot()}api/tools`,
              chunkUploadSize: config.value.chunk_upload_size,
              fileSourcesConfigured: config.value.file_sources_configured,
              ftpUploadSite: config.value.ftp_upload_site,
              defaultDbKey: config.value.default_genome,
              defaultExtension: config.value.default_extension,
          }
        : {};

    return { ...baseOptions, ...configOptions };
}

const options = ref(getDefaultOptions());
const showModal = ref(false);
const content = ref(null);

function dismiss(result) {
    if (result && options.value.callback) {
        options.value.callback(result);
    }

    showModal.value = false;
}

async function open(overrideOptions) {
    const newOptions = overrideOptions ?? {};

    options.value = { ...getDefaultOptions(), ...newOptions };

    if (options.value.callback) {
        options.value.hasCallback = true;
    }

    showModal.value = true;
    await wait(100);

    if (options.value.immediateUpload) {
        content.value.immediateUpload(options.value.immediateFiles);
    }
}

watch(
    () => showModal.value,
    (modalShown) => setIframeEvents(modalShown)
);

function setIframeEvents(disableEvents) {
    const element = document.getElementById("galaxy_main");

    if (element) {
        element.style["pointer-events"] = disableEvents ? "none" : "auto";
    }
}

defineExpose({
    open,
});
</script>

<template>
    <b-modal
        v-model="showModal"
        :static="options.modalStatic"
        header-class="no-separator"
        modal-class="ui-modal"
        dialog-class="upload-dialog"
        body-class="upload-dialog-body"
        no-enforce-focus
        hide-footer>
        <template v-slot:modal-header>
            <h2 class="title h-sm" tabindex="0">{{ options.title }}</h2>
        </template>

        <UploadModalContent
            v-if="currentHistoryId"
            ref="content"
            :key="showModal"
            :current-user-id="currentUser.id"
            :current-history-id="currentHistoryId"
            v-bind="options"
            @dismiss="dismiss" />
    </b-modal>
</template>

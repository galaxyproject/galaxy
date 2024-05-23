<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faFolder, faFolderOpen } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BBreadcrumb, BBreadcrumbItem, BButton, BFormInput } from "bootstrap-vue";
import { computed, ref } from "vue";

import localize from "@/utils/localization";

import FilesDialog from "@/components/FilesDialog/FilesDialog.vue";

library.add(faFolder, faFolderOpen);

const emit = defineEmits<{
    (e: "input", value: string): void;
}>();

const modalKey = ref(0);
const url = ref<URL | null>(null);
const currentDirectoryName = ref("");
const pathChunks = ref<{ pathChunk: string; editable: boolean }[]>([]);

const isValidName = computed(() => {
    if (!currentDirectoryName.value) {
        return null;
    }

    const regex = new RegExp("^(\\w+\\.?)*\\w+$", "g");

    return regex.test(currentDirectoryName.value);
});

// forcing modal to be redrawn
// https://michaelnthiessen.com/force-re-render/
function redrawModal() {
    modalKey.value += 1;
}

function removePath(index: number) {
    pathChunks.value = pathChunks.value.slice(0, index);
}

function reset() {
    url.value = null;
    pathChunks.value = [];
    currentDirectoryName.value = "";

    redrawModal();

    updateURL(true);
}

function removeLastPath(event: KeyboardEvent) {
    // check whether the last item is editable
    if (currentDirectoryName.value === "" && pathChunks.value.length > 0 && pathChunks.value.at(-1)?.editable) {
        // prevent deleting last character on 'currentDirectoryName'
        event.preventDefault();

        currentDirectoryName.value = pathChunks.value.pop()?.pathChunk ?? "";
    }
}

function setUrl(file: { url: string }) {
    url.value = new URL(file.url);

    // split path and keep only valid entries
    pathChunks.value = url.value.href
        .split(/[/\\]/)
        .splice(2)
        .map((x) => ({ pathChunk: x, editable: false }));

    if (file.url) {
        updateURL();
    }
}

function addPath(event: KeyboardEvent) {
    if ((event.key === "Enter" || event.key === "/") && isValidName.value) {
        const newFolder = currentDirectoryName.value;

        pathChunks.value.push({ pathChunk: newFolder, editable: true });

        currentDirectoryName.value = "";

        updateURL();
    }
}

function updateURL(isReset = false) {
    if (!isReset) {
        // create an string of path chunks separated by `/`
        const urlTmp = encodeURI(
            `${url.value?.protocol}//${pathChunks.value.map(({ pathChunk }) => pathChunk).join("/")}`
        );

        if (urlTmp) {
            emit("input", urlTmp);
        }
    }
}
</script>

<template>
    <div>
        <div v-if="!url">
            <BButton id="select-btn" @click="reset">
                <FontAwesomeIcon :icon="faFolderOpen" />
                {{ localize("Select") }}
            </BButton>

            <FilesDialog :key="modalKey" mode="directory" :callback="setUrl" :require-writable="true" />
        </div>

        <BBreadcrumb v-if="url">
            <BBreadcrumbItem title="Select another folder" class="align-items-center" @click="reset">
                <BButton class="pathname" variant="primary">
                    <FontAwesomeIcon :icon="faFolderOpen" />
                    {{ url.protocol }}
                </BButton>
            </BBreadcrumbItem>

            <BBreadcrumbItem
                v-for="({ pathChunk, editable }, index) in pathChunks"
                :key="index"
                class="existent-url-path align-items-center">
                <BButton class="regular-path-chunk" :disabled="!editable" variant="dark" @click="removePath(index)">
                    {{ pathChunk }}
                </BButton>
            </BBreadcrumbItem>

            <BBreadcrumbItem class="directory-input-field align-items-center">
                <BFormInput
                    id="path-input-breadcrumb"
                    v-model="currentDirectoryName"
                    aria-describedby="input-live-help input-live-feedback"
                    :state="isValidName"
                    placeholder="enter directory name"
                    trim
                    @keyup.enter="addPath"
                    @keydown.191.capture.prevent.stop="addPath"
                    @keydown.8.capture="removeLastPath" />
            </BBreadcrumbItem>
        </BBreadcrumb>
    </div>
</template>

<style scoped>
.breadcrumb-item::before {
    font-size: 1.5rem;
}

.directory-input-field a {
    text-decoration: none;
}
</style>

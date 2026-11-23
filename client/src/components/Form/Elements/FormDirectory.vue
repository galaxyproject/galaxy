<script setup lang="ts">
import { faFolderOpen } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BBreadcrumb, BBreadcrumbItem, BFormInput } from "bootstrap-vue";
import { computed, ref, watch } from "vue";

import type { SelectionItem } from "@/components/SelectionDialog/selectionTypes";
import { useToast } from "@/composables/toast";
import localize from "@/utils/localization";
import { errorMessageAsString } from "@/utils/simple-error";

import GButton from "@/components/BaseComponents/GButton.vue";
import FilesDialog from "@/components/FilesDialog/FilesDialog.vue";

interface PathChunk {
    /** URI-encoded folder name */
    pathChunk: string;
    /** Whether the user added this folder, so it can be edited again */
    editable: boolean;
}

interface Props {
    /** Directory URI, e.g. `gxfiles://folder/subfolder` */
    modelValue?: string | null;
}

const props = withDefaults(defineProps<Props>(), {
    modelValue: null,
});

const emit = defineEmits<{
    (e: "update:modelValue", value: string | undefined): void;
}>();

/** Words separated by single dots, e.g. `results` or `run.1` */
const VALID_DIRECTORY_NAME = /^\w+(\.\w+)*$/;

const toast = useToast();
const selectText = localize("Select");

const isModalShown = ref(false);
const modalKey = ref(0);
const url = ref<URL | null>(null);
const pathChunks = ref<PathChunk[]>([]);
const currentDirectoryName = ref("");

/** Last emitted value, to tell our own updates coming back through `modelValue` from outside changes */
let emittedValue: string | undefined = undefined;

const isValidName = computed(() => {
    if (!currentDirectoryName.value) {
        return null;
    }
    return VALID_DIRECTORY_NAME.test(currentDirectoryName.value);
});

const breadcrumbChunks = computed(() =>
    pathChunks.value.map((chunk) => ({ ...chunk, label: decodeURIComponent(chunk.pathChunk) })),
);

function emitValue(value: string | undefined) {
    emittedValue = value;
    emit("update:modelValue", value);
}

function emitPath() {
    if (url.value) {
        const path = pathChunks.value.map(({ pathChunk }) => decodeURIComponent(pathChunk)).join("/");
        emitValue(`${url.value.protocol}//${path}`);
    }
}

function clearDirectory() {
    url.value = null;
    pathChunks.value = [];
    currentDirectoryName.value = "";
}

/** Shows the given directory URI as breadcrumb, returns whether it could be parsed */
function parseUrl(value: string) {
    try {
        url.value = new URL(encodeURI(value));
        pathChunks.value = url.value.href
            .split(/[/\\]/)
            .slice(2)
            .filter((pathChunk) => pathChunk)
            .map((pathChunk) => ({ pathChunk, editable: false }));
        return true;
    } catch (error) {
        toast.error(errorMessageAsString(error), "Invalid directory path");
        return false;
    }
}

/** Shows the given directory as breadcrumb, or clears a missing or unparseable one */
function showDirectory(value: string | null | undefined) {
    currentDirectoryName.value = "";
    if (!value || !parseUrl(value)) {
        clearDirectory();
        emitValue(undefined);
    }
}

function onSelectAnother() {
    clearDirectory();
    // a new key mounts a fresh dialog, starting again at the list of file sources
    modalKey.value += 1;
    isModalShown.value = true;
    emitValue(undefined);
}

function onDirectorySelected(selection: SelectionItem | SelectionItem[]) {
    const item = Array.isArray(selection) ? selection[0] : selection;
    if (item?.url && parseUrl(item.url)) {
        emitPath();
    }
}

function removePath(index: number) {
    pathChunks.value = pathChunks.value.slice(0, index);
    emitPath();
}

function addDirectoryToPath() {
    pathChunks.value.push({ pathChunk: currentDirectoryName.value, editable: true });
    currentDirectoryName.value = "";
    emitPath();
}

function addValidDirectory() {
    if (isValidName.value) {
        addDirectoryToPath();
    }
}

function onSlashKeydown(event: KeyboardEvent) {
    // there is no key modifier for "/", so match on the key name
    if (event.key === "/") {
        event.preventDefault();
        event.stopPropagation();
        addValidDirectory();
    }
}

function onBackspaceKeydown(event: KeyboardEvent) {
    // with an empty input, Backspace moves the last folder the user added back into the input
    const lastChunk = pathChunks.value.at(-1);
    if (currentDirectoryName.value === "" && lastChunk?.editable) {
        event.preventDefault();
        pathChunks.value.pop();
        currentDirectoryName.value = lastChunk.pathChunk;
    }
}

function onBlur() {
    if (currentDirectoryName.value && isValidName.value) {
        addDirectoryToPath();
    } else {
        // propagate the path even if the input was only touched
        emitPath();
    }
}

watch(
    () => props.modelValue,
    (value) => {
        // the parent passes our own emits back; only an outside change replaces the breadcrumb
        if (value !== emittedValue) {
            showDirectory(value);
        }
    },
);

showDirectory(props.modelValue);
</script>

<template>
    <div>
        <div v-if="!url">
            <GButton id="select-btn" @click="onSelectAnother">
                <FontAwesomeIcon :icon="faFolderOpen" /> {{ selectText }}
            </GButton>
            <FilesDialog
                v-if="isModalShown"
                :key="modalKey"
                mode="directory"
                :callback="onDirectorySelected"
                :require-writable="true" />
        </div>
        <BBreadcrumb v-else class="mb-0">
            <BBreadcrumbItem title="Select another folder" class="d-flex align-items-center" @click="onSelectAnother">
                <GButton class="pathname" color="blue">
                    <FontAwesomeIcon :icon="faFolderOpen" /> {{ url.protocol }}
                </GButton>
            </BBreadcrumbItem>
            <BBreadcrumbItem
                v-for="({ label, editable }, index) in breadcrumbChunks"
                :key="index"
                class="existent-url-path d-flex align-items-center">
                <GButton class="regular-path-chunk" :disabled="!editable" @click="removePath(index)">
                    {{ label }}
                </GButton>
            </BBreadcrumbItem>
            <BBreadcrumbItem class="directory-input-field d-flex align-items-center">
                <BFormInput
                    id="path-input-breadcrumb"
                    v-model="currentDirectoryName"
                    aria-describedby="input-live-help input-live-feedback"
                    :state="isValidName"
                    placeholder="enter directory name"
                    trim
                    @keyup.enter="addValidDirectory"
                    @keydown.capture="onSlashKeydown"
                    @keydown.backspace.capture="onBackspaceKeydown"
                    @blur="onBlur" />
            </BBreadcrumbItem>
        </BBreadcrumb>

        <div v-if="modelValue" class="px-2" data-description="directory full path">
            <span v-localize>Directory Path:</span>
            <code>{{ modelValue }}</code>
        </div>
    </div>
</template>

<style scoped>
.breadcrumb-item::before {
    font-size: 1.5rem;
}
.directory-input-field {
    flex: 1 1 10rem;
}
.directory-input-field :deep(a) {
    flex: 1 1 auto;
    text-decoration: none;
}
</style>

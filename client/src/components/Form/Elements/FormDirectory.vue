<template>
    <div>
        <div v-if="!url">
            <GButton id="select-btn" @click="reset">
                <FontAwesomeIcon :icon="faFolderOpen" /> {{ selectText }}
            </GButton>
            <FilesDialog
                v-if="isModalShown"
                :key="modalKey"
                mode="directory"
                :callback="setUrl"
                :require-writable="true" />
        </div>
        <BBreadcrumb v-if="url" class="mb-0">
            <BBreadcrumbItem title="Select another folder" class="d-flex align-items-center" @click="reset">
                <GButton class="pathname" color="blue">
                    <FontAwesomeIcon :icon="faFolderOpen" /> {{ url.protocol }}
                </GButton>
            </BBreadcrumbItem>
            <BBreadcrumbItem
                v-for="({ pathChunk, editable }, index) in pathChunks"
                :key="index"
                class="existent-url-path d-flex align-items-center">
                <GButton class="regular-path-chunk" :disabled="!editable" @click="removePath(index)">
                    {{ decodeURIComponent(pathChunk) }}
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
                    @keyup.enter="addPath"
                    @keydown.capture="onSlashKeydown"
                    @keydown.backspace.capture="removeLastPath"
                    @blur="handleBlur" />
            </BBreadcrumbItem>
        </BBreadcrumb>

        <div v-if="modelValue" class="px-2" data-description="directory full path">
            <span v-localize>Directory Path:</span>
            <code>{{ modelValue }}</code>
        </div>
    </div>
</template>

<script>
import { faFolderOpen } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BBreadcrumb, BBreadcrumbItem, BFormInput } from "bootstrap-vue";

import { FilesDialog } from "@/components/FilesDialog";
import { Toast } from "@/composables/toast";
import _l from "@/utils/localization";
import { errorMessageAsString } from "@/utils/simple-error";

import GButton from "@/components/BaseComponents/GButton.vue";

const getDefaultValues = () => ({
    isModalShown: false,
    url: "",
    pathChunks: "",
    currentDirectoryName: "",
});

export default {
    components: {
        BBreadcrumb,
        BBreadcrumbItem,
        BFormInput,
        FontAwesomeIcon,
        FilesDialog,
        GButton,
    },
    props: {
        modelValue: {
            type: String,
            default: null,
        },
    },
    emits: ["update:modelValue"],
    data() {
        return {
            ...getDefaultValues(),
            emittedValue: undefined,
            modalKey: 0,
            selectText: _l("Select"),
            faFolderOpen,
        };
    },
    computed: {
        isValidName() {
            if (!this.currentDirectoryName) {
                return null;
            }
            const regex = new RegExp("^(\\w+\\.?)*\\w+$", "g");
            return regex.test(this.currentDirectoryName);
        },
    },
    watch: {
        modelValue(value) {
            // the parent passes our own emits back; only an outside change replaces the breadcrumb
            if (value !== this.emittedValue) {
                this.showDirectory(value);
            }
        },
    },
    created() {
        this.showDirectory(this.modelValue);
    },
    methods: {
        /** Shows the given directory as breadcrumb, or clears a missing or unparseable one */
        showDirectory(value) {
            this.currentDirectoryName = "";
            if (!value || !this.parseUrl(value)) {
                this.url = "";
                this.pathChunks = "";
                this.updateURL(true);
            }
        },
        removePath(index) {
            this.pathChunks = this.pathChunks.slice(0, index);
            this.updateURL();
        },
        reset() {
            const data = getDefaultValues();
            Object.keys(data).forEach((k) => (this[k] = data[k]));
            this.redrawModal();
            this.updateURL(true);
        },
        // forcing modal to be redrawn
        // https://michaelnthiessen.com/force-re-render/
        redrawModal() {
            this.modalKey += 1;
            this.isModalShown = true;
        },
        removeLastPath(event) {
            // check whether the last item is editable
            if (this.currentDirectoryName === "" && this.pathChunks.length > 0 && this.pathChunks.at(-1).editable) {
                // prevent deleting last character on 'currentDirectoryName'
                event.preventDefault();
                this.currentDirectoryName = this.pathChunks.pop().pathChunk;
            }
        },
        setUrl({ url }) {
            if (url && this.parseUrl(url)) {
                this.updateURL();
            }
        },
        /** Shows the given directory URI as breadcrumb, returns whether it could be parsed */
        parseUrl(url) {
            try {
                this.url = new URL(encodeURI(url));
                // split path and keep only valid entries
                this.pathChunks = this.url.href
                    .split(/[/\\]/)
                    .splice(2)
                    .filter((pathChunk) => pathChunk)
                    .map((x) => ({ pathChunk: x, editable: false }));
                return true;
            } catch (error) {
                Toast.error(errorMessageAsString(error), "Invalid directory path");
                return false;
            }
        },
        onSlashKeydown(event) {
            // Vue 3 dropped keyCode modifiers and has no modifier for "/", so match on the key name.
            if (event.key === "/") {
                event.preventDefault();
                event.stopPropagation();
                this.addPath(event);
            }
        },
        addPath({ key }) {
            if ((key === "Enter" || key === "/") && this.isValidName) {
                this.addDirectoryToPath();
            }
        },
        handleBlur() {
            if (this.currentDirectoryName && this.isValidName) {
                this.addDirectoryToPath();
            } else {
                // If the input was touched let's propagate the change either way.
                this.updateURL();
            }
        },
        addDirectoryToPath() {
            const newFolder = this.currentDirectoryName;
            this.pathChunks.push({ pathChunk: newFolder, editable: true });
            this.currentDirectoryName = "";
            this.updateURL();
        },
        updateURL(isReset = false) {
            let url = undefined;
            if (!isReset) {
                // create an string of path chunks separated by `/`
                url = encodeURI(
                    `${this.url.protocol}//${this.pathChunks
                        .map(({ pathChunk }) => decodeURIComponent(pathChunk))
                        .join("/")}`,
                );
                url = decodeURI(url);
            }
            this.emittedValue = url;
            this.$emit("update:modelValue", url);
        },
    },
};
</script>

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

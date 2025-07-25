<template>
    <div>
        <div v-if="!url">
            <GButton id="select-btn" @click="reset"> <FontAwesomeIcon icon="folder-open" /> {{ selectText }} </GButton>
            <FilesDialog
                :key="modalKey"
                mode="directory"
                :callback="setUrl"
                :require-writable="true"
                :is-open="isModalShown" />
        </div>
        <b-breadcrumb v-if="url" class="mb-0">
            <b-breadcrumb-item title="Select another folder" class="align-items-center" @click="reset">
                <GButton class="pathname" color="blue">
                    <FontAwesomeIcon icon="folder-open" /> {{ url.protocol }}
                </GButton>
            </b-breadcrumb-item>
            <b-breadcrumb-item
                v-for="({ pathChunk, editable }, index) in pathChunks"
                :key="index"
                class="existent-url-path align-items-center">
                <GButton class="regular-path-chunk" :disabled="!editable" @click="removePath(index)">
                    {{ decodeURIComponent(pathChunk) }}
                </GButton>
            </b-breadcrumb-item>
            <b-breadcrumb-item class="directory-input-field align-items-center">
                <b-input
                    id="path-input-breadcrumb"
                    v-model="currentDirectoryName"
                    aria-describedby="input-live-help input-live-feedback"
                    :state="isValidName"
                    placeholder="enter directory name"
                    trim
                    @keyup.enter="addPath"
                    @keydown.191.capture.prevent.stop="addPath"
                    @keydown.8.capture="removeLastPath" />
            </b-breadcrumb-item>
        </b-breadcrumb>

        <div v-if="value" class="px-2" data-description="directory full path">
            <span v-localize>Directory Path:</span>
            <code>{{ value }}</code>
        </div>
    </div>
</template>

<script>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faFolder, faFolderOpen } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { FilesDialog } from "components/FilesDialog";
import { Toast } from "composables/toast";
import _l from "utils/localization";

import { errorMessageAsString } from "@/utils/simple-error";

import GButton from "@/components/BaseComponents/GButton.vue";

library.add(faFolder, faFolderOpen);

const getDefaultValues = () => ({
    isModalShown: false,
    url: "",
    pathChunks: "",
    currentDirectoryName: "",
});

export default {
    components: {
        FontAwesomeIcon,
        FilesDialog,
        GButton,
    },
    props: {
        value: {
            type: String,
            default: null,
        },
    },
    data() {
        return { ...getDefaultValues(), modalKey: 0, selectText: _l("Select") };
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
    mounted() {
        this.updateURL(true);
    },
    methods: {
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
            try {
                this.url = new URL(encodeURI(url));
                // split path and keep only valid entries
                this.pathChunks = this.url.href
                    .split(/[/\\]/)
                    .splice(2)
                    .map((x) => ({ pathChunk: x, editable: false }));

                if (url) {
                    this.updateURL();
                }
            } catch (error) {
                Toast.error(errorMessageAsString(error), "Invalid directory path");
            }
        },
        addPath({ key }) {
            if ((key === "Enter" || key === "/") && this.isValidName) {
                const newFolder = this.currentDirectoryName;
                this.pathChunks.push({ pathChunk: newFolder, editable: true });
                this.currentDirectoryName = "";
                this.updateURL();
            }
        },
        updateURL(isReset = false) {
            let url = undefined;
            if (!isReset) {
                // create an string of path chunks separated by `/`
                url = encodeURI(
                    `${this.url.protocol}//${this.pathChunks
                        .map(({ pathChunk }) => decodeURIComponent(pathChunk))
                        .join("/")}`
                );
                url = decodeURI(url);
            }
            this.$emit("input", url);
        },
    },
};
</script>

<style scoped>
.breadcrumb-item::before {
    font-size: 1.5rem;
}
.directory-input-field a {
    text-decoration: none;
}
</style>

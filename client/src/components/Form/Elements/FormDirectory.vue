<template>
    <div>
        <div v-if="!url">
            <b-button id="select-btn" @click="reset">
                <font-awesome-icon icon="folder-open" /> {{ selectText }}
            </b-button>
            <FilesDialog :key="modalKey" mode="directory" :callback="setUrl" :require-writable="true" />
        </div>
        <b-breadcrumb v-if="url">
            <b-breadcrumb-item title="Select another folder" class="align-items-center" @click="reset">
                <b-button class="pathname" variant="primary">
                    <font-awesome-icon icon="folder-open" /> {{ url.protocol }}</b-button
                >
            </b-breadcrumb-item>
            <b-breadcrumb-item
                v-for="({ pathChunk, editable }, index) in pathChunks"
                :key="index"
                class="existent-url-path align-items-center">
                <b-button class="regular-path-chunk" :disabled="!editable" variant="dark" @click="removePath(index)">
                    {{ pathChunk }}</b-button
                >
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
    </div>
</template>

<script>
import { library } from "@fortawesome/fontawesome-svg-core";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faFolder, faFolderOpen } from "@fortawesome/free-solid-svg-icons";
import { FilesDialog } from "components/FilesDialog";
import _l from "utils/localization";

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
    methods: {
        removePath(index) {
            this.pathChunks = this.pathChunks.slice(0, index);
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
            this.url = new URL(url);
            // split path and keep only valid entries
            this.pathChunks = this.url.pathname
                .split("/")
                .filter((pathChunk) => pathChunk)
                .map((x) => ({ pathChunk: x, editable: false }));

            if (url) {
                this.updateURL();
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
                url = encodeURI(`${this.url.protocol}//${this.pathChunks.map(({ pathChunk }) => pathChunk).join("/")}`);
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

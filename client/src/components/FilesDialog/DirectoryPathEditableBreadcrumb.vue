<template>
    <div>
        <div v-if="!url">
            <b-button @click="reset"> <font-awesome-icon icon="folder-open" /> Select folder </b-button>
            <FilesDialog :key="modalKey" mode="directory" :callback="setUrl" :require-writable="true" />
        </div>
        <b-breadcrumb v-if="url">
            <b-breadcrumb-item title="Select another folder" @click="reset" class="align-items-center">
                <b-button pill variant="primary"> <font-awesome-icon icon="folder-open" /> {{ url.protocol }}</b-button>
            </b-breadcrumb-item>
            <b-breadcrumb-item
                v-for="({ name, editable }, index) in pathChunks"
                :key="index"
                class="existent-url-path align-items-center"
            >
                <b-button @click="removePath(index)" pill :disabled="!editable" variant="dark"> {{ name }}</b-button>
            </b-breadcrumb-item>
            <b-breadcrumb-item class="directory-input-field align-items-center">
                <b-input
                    aria-describedby="input-live-help input-live-feedback"
                    :state="isValidName"
                    @keyup.enter="addPath"
                    @keydown.191.capture.prevent.stop="addPath"
                    v-model="currentDirectoryName"
                    placeholder="enter directory name"
                    trim
                />
            </b-breadcrumb-item>
        </b-breadcrumb>
    </div>
</template>

<script>
import { library } from "@fortawesome/fontawesome-svg-core";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faFolder, faFolderOpen } from "@fortawesome/free-solid-svg-icons";
import { FilesDialog } from "components/FilesDialog";

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
        return { ...getDefaultValues(), modalKey: 0 };
    },
    props: {
        callback: {
            type: Function,
            required: true,
        },
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
            console.debug("reset");
            this.updateURL(true)

        },
        // forcing modal to be redrawn
        // https://michaelnthiessen.com/force-re-render/
        redrawModal() {
            this.modalKey += 1;
        },
        setUrl({ url }) {
            this.url = new URL(url);
            // split path and keep only valid entries
            this.pathChunks = this.url.pathname
                .split("/")
                .filter((path) => path)
                .map((x) => ({ name: x, editable: false }));
            this.updateURL();
        },
        addPath({ key }) {
            if (key === "Enter" || (key === "/" && this.isValidName)) {
                const newFolder = this.currentDirectoryName.replaceAll("/", "");
                this.pathChunks.push({ name: newFolder, editable: true });
                this.currentDirectoryName = "";
                this.updateURL();
            }
        },
        updateURL(isReset = false) {
            let url = undefined;
            if (!isReset) {
                url = `${this.url.protocol}//${this.pathChunks.map(({ name }) => name).join("/")}`;
            }
            this.callback(url);
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

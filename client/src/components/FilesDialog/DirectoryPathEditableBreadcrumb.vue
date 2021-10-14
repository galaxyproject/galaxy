<template>
    <b-breadcrumb>
        <b-breadcrumb-item>
            <b-dropdown class="justify-content-md-center">
                <template v-slot:button-content>
                    <font-awesome-icon icon="plug" />
                    {{ currentSource ? currentSource.doc : "Choose your remote" }}
                </template>
                <b-dropdown-item
                    @click="currentSource = fileSource"
                    v-for="(fileSource, index) in remoteFileSources"
                    :key="index"
                    >{{ fileSource.doc }}</b-dropdown-item
                >
            </b-dropdown>
        </b-breadcrumb-item>
        <b-breadcrumb-item v-for="(chunk, index) in pathChunks" :key="index" class="d-flex align-items-center">
            {{ chunk }}
        </b-breadcrumb-item>
        <b-breadcrumb-item class="directory-input-field">
            <b-input
                aria-describedby="input-live-help input-live-feedback"
                :state="isValidName"
                @keyup.enter="addPath"
                @keydown.191.capture.prevent.stop="addPath"
                v-model="directoryName"
                placeholder="Name your directory..."
                trim
            />
            <b-form-invalid-feedback id="input-live-feedback">
                Your directory name contains invalid characters
            </b-form-invalid-feedback>
            <b-form-text id="input-live-help"> Please enter directory name and press enter or "/" </b-form-text>
        </b-breadcrumb-item>
    </b-breadcrumb>
</template>

<script>
import { library } from "@fortawesome/fontawesome-svg-core";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faPlug } from "@fortawesome/free-solid-svg-icons";
import { Services } from "./services";

library.add(faPlug);

export default {
    components: {
        FontAwesomeIcon,
    },
    data() {
        return {
            remoteFileSources: [],
            pathChunks: [],
            currentSource: undefined,
            directoryName: "",
        };
    },
    created() {
        new Services().getFileSources().then((items) => {
            this.remoteFileSources = items;
        });
    },
    props: {
        callback: {
            type: Function,
            default: () => {},
        },
        title: {
            type: String,
            default: "copy to clipboard",
            required: false,
        },
    },
    computed: {
        isValidName() {
            if (!this.directoryName) {
                return null;
            }
            const regex = new RegExp("^(\\w+\\.?)*\\w+$", "g");
            return regex.test(this.directoryName);
        },
    },
    methods: {
        addPath({ key }) {
            if (key === "Enter" || (key === "/" && this.isValidName)) {
                this.pathChunks.push(this.directoryName.replaceAll("/", ""));
                this.directoryName = "";
            }
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

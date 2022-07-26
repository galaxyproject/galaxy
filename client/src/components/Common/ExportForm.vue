<template>
    <div>
        <b-form-group
            id="fieldset-directory"
            label-for="directory"
            :description="directoryDescription | localize"
            class="mt-3">
            <files-input id="directory" v-model="directory" mode="directory" :require-writable="true" />
        </b-form-group>
        <b-form-group id="fieldset-name" label-for="name" :description="nameDescription | localize" class="mt-3">
            <b-form-input id="name" v-model="name" :placeholder="namePlaceholder | localize" required></b-form-input>
        </b-form-group>
        <b-row align-h="end">
            <b-col
                ><b-button class="export-button" variant="primary" :disabled="!canExport" @click.prevent="doExport">{{
                    exportButtonText | localize
                }}</b-button></b-col
            >
        </b-row>
    </div>
</template>

<script>
import FilesInput from "components/FilesDialog/FilesInput.vue";

export default {
    components: {
        FilesInput,
    },
    props: {
        what: {
            type: String,
            default: "archive",
        },
    },
    data() {
        return {
            directory: null,
            name: null,
        };
    },
    computed: {
        directoryDescription() {
            return `Select a 'remote files' directory to export ${this.what} to.`;
        },
        nameDescription() {
            return "Give the exported file a name.";
        },
        namePlaceholder() {
            return "Name";
        },
        exportButtonText() {
            return "Export";
        },
        canExport() {
            return !!this.name && !!this.directory;
        },
    },
    methods: {
        doExport() {
            this.$emit("export", this.directory, this.name);
        },
    },
};
</script>

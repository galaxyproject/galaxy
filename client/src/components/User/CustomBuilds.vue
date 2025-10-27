<template>
    <div>
        <BreadcrumbHeading :items="breadcrumbItems" />

        <GTable compact show-empty :items="customBuilds" :fields="fields" class="mb-3">
            <template v-slot:cell(action)="row">
                <GLink tooltip title="Delete build" @click="deleteBuild(row.item.id)">
                    <FontAwesomeIcon :icon="faTrash" />
                </GLink>
            </template>
        </GTable>

        <template v-if="installedBuilds.length > 0">
            <BRow class="mt-2">
                <BCol>
                    <h2 class="h-sm">System Installed Builds</h2>
                </BCol>
            </BRow>

            <BRow>
                <BCol id="installed-builds" class="mb-4">
                    <Multiselect
                        id="installed-builds"
                        v-model="selectedInstalledBuilds"
                        name="installed-builds"
                        multiple
                        taggable
                        label="label"
                        select-label=""
                        deselect-label=""
                        track-by="value"
                        :searchable="false"
                        :options="installedBuilds" />
                </BCol>
            </BRow>
        </template>

        <BRow>
            <BCol>
                <h2 class="h-sm">Add a Custom Build</h2>
            </BCol>
        </BRow>

        <BRow>
            <BCol>
                <BCard>
                    <BAlert
                        fade
                        dismissible
                        :variant="alertType"
                        :show="dismissCountDown"
                        @dismissed="dismissCountDown = 0"
                        @dismiss-count-down="countDownChanged">
                        {{ alertMessage }}
                    </BAlert>

                    <BForm @submit.prevent="save">
                        <BFormGroup label="Name" description="Specify a build name, e.g. Hamster." label-for="name">
                            <BFormInput id="name" v-model="form.name" tour_id="name" required />
                        </BFormGroup>

                        <BFormGroup label="Key" description="Specify a build key, e.g. hamster_v1." label-for="id">
                            <BFormInput id="id" v-model="form.id" tour_id="id" required />
                        </BFormGroup>

                        <BFormGroup label="Definition" description="Provide the data source." label-for="type">
                            <BFormSelect
                                id="type"
                                v-model="selectedDataSource"
                                tour_id="type"
                                :options="dataSources"></BFormSelect>
                        </BFormGroup>

                        <div>
                            <BFormGroup v-if="selectedDataSource === 'fasta'" label="FASTA-file">
                                <BFormSelect
                                    v-model="selectedFastaFile"
                                    :options="fastaFiles"
                                    :disabled="fastaFilesSelectDisabled"></BFormSelect>
                            </BFormGroup>

                            <BFormGroup v-if="selectedDataSource === 'file'" label="Len-file">
                                <BFormFile placeholder="Choose a file..." @change="readFile" />

                                <BProgress
                                    v-show="fileLoaded !== 0"
                                    animated
                                    show-progress
                                    :value="fileLoaded"
                                    :max="maxFileSize" />

                                <BFormTextarea v-show="form.file" :value="form.file" />
                            </BFormGroup>

                            <BFormGroup v-if="selectedDataSource === 'text'" label="Edit/Paste">
                                <BFormTextarea id="len-file-text-area" v-model="form.text" />
                            </BFormGroup>
                        </div>

                        <BButton
                            id="save"
                            v-g-tooltip.bottom.hover
                            type="submit"
                            variant="primary"
                            title="Create new build">
                            <FontAwesomeIcon :icon="faSave" />
                            Save
                        </BButton>
                    </BForm>
                </BCard>
            </BCol>

            <BCol>
                <BCard v-if="selectedDataSource === 'fasta'" class="alert-info">
                    <h2 class="h-sm">FASTA format</h2>
                    <p class="card-text">
                        This is a multi-fasta file from your current history that provides the genome sequences for each
                        chromosome/contig in your build.
                    </p>
                    <p class="card-text">Here is a snippet from an example multi-fasta file:</p>
                    <pre class="card-text">
&gt;chr1
ATTATATATAAGACCACAGAGAGAATATTTTGCCCGG...

&gt;chr2
GGCGGCCGCGGCGATATAGAACTACTCATTATATATA...

...
                    </pre>
                </BCard>
                <BCard v-else class="alert-info">
                    <h2 class="h-sm">Length Format</h2>
                    <p class="card-text">The length format is two-column, separated by whitespace, of the form:</p>
                    <pre class="card-text">chrom/contig   length of chrom/contig</pre>
                    <p class="card-text">For example, the first few entries of <em>mm9.len</em> are as follows:</p>
                    <pre class="card-text">
chr1    197195432
chr2    181748087
chr3    159599783
chr4    155630120
chr5    152537259
                    </pre>
                </BCard>
            </BCol>
        </BRow>
    </div>
</template>

<script>
import "vue-multiselect/dist/vue-multiselect.css";

import { faSave, faTrash } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import axios from "axios";
import {
    BAlert,
    BButton,
    BCard,
    BCol,
    BForm,
    BFormFile,
    BFormGroup,
    BFormInput,
    BFormSelect,
    BFormTextarea,
    BProgress,
    BRow,
} from "bootstrap-vue";
import Multiselect from "vue-multiselect";

import { getGalaxyInstance } from "@/app";
import { useHistoryStore } from "@/stores/historyStore";
import { withPrefix } from "@/utils/redirect";

import GLink from "@/components/BaseComponents/GLink.vue";
import BreadcrumbHeading from "@/components/Common/BreadcrumbHeading.vue";
import GTable from "@/components/Common/GTable.vue";

export default {
    components: {
        BAlert,
        BButton,
        BCard,
        BCol,
        BForm,
        BFormFile,
        BFormGroup,
        BFormInput,
        BFormSelect,
        BFormTextarea,
        BProgress,
        BreadcrumbHeading,
        BRow,
        FontAwesomeIcon,
        GLink,
        GTable,
        Multiselect,
    },
    data() {
        const Galaxy = getGalaxyInstance();
        return {
            faSave,
            faTrash,
            breadcrumbItems: [{ title: "User Preferences", to: "/user" }, { title: "Current Custom Builds" }],
            customBuildsUrl: withPrefix(`/api/users/${Galaxy.user.id}/custom_builds`),
            selectedInstalledBuilds: [],
            installedBuilds: [],
            maxFileSize: 100,
            fileLoaded: 0,
            fields: [
                { key: "name", label: "Name" },
                { key: "id", label: "Key" },
                { key: "count", label: "Number of chroms/contigs" },
                { key: "action", label: "" },
            ],
            customBuilds: [],
            alertType: "info",
            alertMessage: "",
            dismissSecs: 5,
            dismissCountDown: 0,
            form: {
                id: "",
                name: "",
                file: "",
                text: "",
            },
            dataSources: [
                { value: "fasta", text: "FASTA-file from history" },
                { value: "file", text: "Len-file from disk" },
                { value: "text", text: "Len-file by copy/paste" },
            ],
            selectedDataSource: "fasta",
            fastaFilesLoading: true,
            fastaFilesSelectDisabled: true,
            fastaFiles: [],
            selectedFastaFile: null,
        };
    },
    computed: {
        lengthType: function () {
            return this.selectedDataSource || "";
        },
        lengthValue: function () {
            let value = "";
            if (this.lengthType === "fasta") {
                value = this.selectedFastaFile || "";
            } else if (this.lengthType === "file") {
                value = this.form.file;
            } else if (this.lengthType === "text") {
                value = this.form.text;
            }
            return value;
        },
    },
    async created() {
        const { loadCurrentHistoryId } = useHistoryStore();
        const historyId = await loadCurrentHistoryId();
        this.loadCustomBuilds();
        if (historyId) {
            this.loadCustomBuildsMetadata(historyId);
        } else {
            this.fastaFilesLoading = false;
        }
    },
    methods: {
        loadCustomBuilds() {
            axios
                .get(this.customBuildsUrl)
                .then((response) => {
                    this.customBuilds = response.data;
                })
                .catch((error) => {
                    this.showAlert("danger", error.response);
                });
        },
        loadCustomBuildsMetadata(historyId) {
            axios
                .get(withPrefix(`/api/histories/${historyId}/custom_builds_metadata`))
                .then((response) => {
                    const fastaHdas = response.data.fasta_hdas;
                    for (let i = 0; i < fastaHdas.length; i++) {
                        fastaHdas[i].text = fastaHdas[i].label;
                    }
                    if (fastaHdas && fastaHdas.length > 0) {
                        this.fastaFiles = fastaHdas;
                        this.selectedFastaFile = fastaHdas[0].value;
                        this.fastaFilesSelectDisabled = false;
                    }
                    this.fastaFilesLoading = false;
                    this.installedBuilds = response.data.installed_builds;
                    for (let i = 0; i < this.installedBuilds.length; i++) {
                        this.installedBuilds[i].text = this.installedBuilds[i].label;
                    }
                })
                .catch((error) => {
                    this.showAlert("danger", error.response);
                    this.fastaFilesLoading = false;
                });
        },
        save(event) {
            const data = {
                id: this.form.id,
                name: this.form.name,
                "len|type": this.lengthType,
                "len|value": this.lengthValue,
            };
            if (!data.id.trim() || !data.name.trim() || !data["len|value"].trim()) {
                this.showAlert("danger", "All inputs are required.");
                return false;
            }
            axios
                .put(`${this.customBuildsUrl}/${data.id}`, data)
                .then((response) => {
                    if (response.data.message) {
                        this.showAlert("warning", response.data.message);
                    } else {
                        this.showAlert("success", "Successfully added a new custom build.");
                    }
                    this.loadCustomBuilds();
                })
                .catch((error) => {
                    const message = error.response.data.err_msg;
                    this.showAlert("danger", message || "Failed to create custom build.");
                });
        },
        deleteBuild(id) {
            axios
                .delete(`${this.customBuildsUrl}/${id}`)
                .then((response) => {
                    this.customBuilds = this.customBuilds.filter((i) => i.id !== id);
                })
                .catch((error) => {
                    const message = error.response.data.err_msg;
                    this.showAlert("danger", message || "Failed to delete custom build.");
                });
        },
        readFile(event) {
            const file = event.target.files && event.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onprogress = (e) => {
                    if (e.lengthComputable) {
                        this.fileLoaded = Math.round(e.loaded / e.total) * 100;
                    }
                };
                reader.onload = () => {
                    this.fileLoaded = 0;
                    this.form.file = reader.result;
                };
                reader.readAsText(file);
            }
        },
        showAlert(type, message) {
            this.alertType = type;
            this.alertMessage = message;
            this.dismissCountDown = this.dismissSecs;
        },
        countDownChanged(dismissCountDown) {
            this.dismissCountDown = dismissCountDown;
        },
    },
};
</script>

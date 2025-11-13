<script setup lang="ts">
import {
    faClipboard,
    faCloud,
    faColumns,
    faCompass,
    faDatabase,
    faDesktop,
    faFileArchive,
    faHdd,
    faLink,
    faSitemap,
    faSlidersH,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";
import { computed, ref } from "vue";

import GModal from "@/components/BaseComponents/GModal.vue";
import ButtonPlain from "@/components/Common/ButtonPlain.vue";
import DelayedInput from "@/components/Common/DelayedInput.vue";
import ActivityPanel from "@/components/Panels/ActivityPanel.vue";
import ScrollList from "@/components/ScrollList/ScrollList.vue";

type UploadMode =
    | "local-file"
    | "paste-content"
    | "paste-links"
    | "collection-upload"
    | "remote-files"
    | "data-library"
    | "explore-zip"
    | "import-history"
    | "import-workflow";

interface UploadMethod {
    id: UploadMode;
    name: string;
    description: string;
    icon: any;
}

const query = ref("");
const showModal = ref(false);
const showGuidedModal = ref(false);
const showAdvancedModal = ref(false);
const selectedMethod = ref<UploadMethod | null>(null);

const uploadMethods: UploadMethod[] = [
    {
        id: "local-file",
        name: "Upload from Computer",
        description: "Select and upload files from your local device",
        icon: faDesktop,
    },
    {
        id: "paste-content",
        name: "Paste File Content",
        description: "Paste the content of a file directly",
        icon: faClipboard,
    },
    {
        id: "paste-links",
        name: "Paste Links/URLs",
        description: "Paste URLs to fetch and import data from remote sources",
        icon: faLink,
    },
    {
        id: "collection-upload",
        name: "Upload File Collection",
        description: "Upload multiple files as a collection",
        icon: faColumns,
    },
    {
        id: "remote-files",
        name: "Choose Remote Files",
        description: "Select files from configured remote file sources or file repositories",
        icon: faCloud,
    },
    {
        id: "data-library",
        name: "Import from Data Library",
        description: "Select files from Galaxy's data library",
        icon: faDatabase,
    },
    {
        id: "explore-zip",
        name: "Explore Compressed Zip Archive",
        description: "Browse and select files directly from a compressed zip archive either locally or remotely",
        icon: faFileArchive,
    },
    {
        id: "import-history",
        name: "Import History",
        description: "Import an entire history from a file or URL",
        icon: faHdd,
    },
    {
        id: "import-workflow",
        name: "Import Workflow",
        description: "Import a workflow from a file or URL",
        icon: faSitemap,
    },
];

const filteredMethods = computed(() => {
    const rawTokens = query.value.trim().split(/\s+/).filter(Boolean);
    if (rawTokens.length === 0) {
        return uploadMethods;
    }
    const tokens = rawTokens.map((token) => token.toLowerCase());
    return uploadMethods.filter((method) => {
        const searchText = `${method.name} ${method.description}`.toLowerCase();
        return tokens.every((token) => searchText.includes(token));
    });
});

function selectUploadMethod(method: UploadMethod) {
    console.log("selectUploadMethod called with:", method);
    selectedMethod.value = method;
    showModal.value = true;
    console.log("showModal set to:", showModal.value);
    console.log("selectedMethod set to:", selectedMethod.value);
}

function closeModal() {
    showModal.value = false;
    selectedMethod.value = null;
}

function openAdvancedMode() {
    showAdvancedModal.value = true;
}

function openGuidedMode() {
    showGuidedModal.value = true;
}
</script>

<template>
    <div class="upload-panel-wrapper">
        <ActivityPanel title="Import Data" data-description="beta upload panel">
            <template v-slot:header-buttons>
                <BButton
                    v-b-tooltip.hover.bottom.noninteractive
                    title="Import data using a guided wizard"
                    variant="link"
                    size="sm"
                    @click="openGuidedMode">
                    <FontAwesomeIcon :icon="faCompass" fixed-width />
                    Guided
                </BButton>
                <BButton
                    v-b-tooltip.hover.bottom.noninteractive
                    title="Advanced mode"
                    variant="link"
                    size="sm"
                    @click="openAdvancedMode">
                    <FontAwesomeIcon :icon="faSlidersH" fixed-width />
                    Advanced
                </BButton>
            </template>
            <template v-slot:header>
                <DelayedInput :delay="100" class="my-2" placeholder="Search upload methods" @change="query = $event" />
            </template>
            <ScrollList
                :item-key="(method) => method.id"
                :in-panel="true"
                name="upload method"
                name-plural="upload methods"
                load-disabled
                :prop-items="filteredMethods"
                :prop-total-count="uploadMethods.length"
                :prop-busy="false">
                <template v-slot:item="{ item: method }">
                    <ButtonPlain
                        class="upload-method-item rounded p-3 mb-2"
                        :data-method-id="method.id"
                        @click="selectUploadMethod(method)">
                        <div class="d-flex align-items-start">
                            <div class="upload-method-icon mr-3">
                                <FontAwesomeIcon :icon="method.icon" size="2x" class="text-primary" />
                            </div>
                            <div class="text-left flex-grow-1">
                                <div class="upload-method-title font-weight-bold mb-1">
                                    {{ method.name }}
                                </div>
                                <div class="upload-method-description text-muted small">
                                    {{ method.description }}
                                </div>
                            </div>
                        </div>
                    </ButtonPlain>
                </template>
            </ScrollList>
        </ActivityPanel>

        <GModal :show.sync="showModal" :title="selectedMethod?.name || 'Import Data'" size="large" footer>
            <template v-slot:body>
                <div v-if="selectedMethod" class="upload-modal-content">
                    <!-- Dynamic content based on selected method -->
                    <div v-if="selectedMethod.id === 'local-file'">
                        <p>{{ selectedMethod.description }}</p>
                        <!-- TODO: Add local file upload interface here -->
                        <p class="text-muted">Local file upload interface will go here...</p>
                    </div>

                    <div v-else-if="selectedMethod.id === 'paste-content'">
                        <p>{{ selectedMethod.description }}</p>
                        <!-- TODO: Add paste content interface here -->
                        <p class="text-muted">Paste file content interface will go here...</p>
                    </div>

                    <div v-else-if="selectedMethod.id === 'paste-links'">
                        <p>{{ selectedMethod.description }}</p>
                        <!-- TODO: Add paste links interface here -->
                        <p class="text-muted">Paste links/URLs interface will go here...</p>
                    </div>

                    <div v-else-if="selectedMethod.id === 'collection-upload'">
                        <p>{{ selectedMethod.description }}</p>
                        <!-- TODO: Add collection upload interface here -->
                        <p class="text-muted">Collection upload interface will go here...</p>
                    </div>

                    <div v-else-if="selectedMethod.id === 'remote-files'">
                        <p>{{ selectedMethod.description }}</p>
                        <!-- TODO: Add remote file browser here -->
                        <p class="text-muted">Remote file browser will go here...</p>
                    </div>

                    <div v-else-if="selectedMethod.id === 'data-library'">
                        <p>{{ selectedMethod.description }}</p>
                        <!-- TODO: Add data library browser here -->
                        <p class="text-muted">Data library browser will go here...</p>
                    </div>

                    <div v-else-if="selectedMethod.id === 'explore-zip'">
                        <p>{{ selectedMethod.description }}</p>
                        <!-- TODO: Add zip archive explorer here -->
                        <p class="text-muted">Zip archive explorer will go here...</p>
                    </div>

                    <div v-else-if="selectedMethod.id === 'import-history'">
                        <p>{{ selectedMethod.description }}</p>
                        <!-- TODO: Add history import interface here -->
                        <p class="text-muted">History import interface will go here...</p>
                    </div>

                    <div v-else-if="selectedMethod.id === 'import-workflow'">
                        <p>{{ selectedMethod.description }}</p>
                        <!-- TODO: Add workflow import interface here -->
                        <p class="text-muted">Workflow import interface will go here...</p>
                    </div>
                </div>
            </template>

            <template v-slot:footer>
                <BButton variant="secondary" @click="closeModal">Cancel</BButton>
                <BButton variant="primary" @click="closeModal">Start Import</BButton>
            </template>
        </GModal>

        <GModal :show.sync="showGuidedModal" title="Guided Import Wizard" size="large" footer>
            <template v-slot:body>
                <div class="guided-wizard-content">
                    <h4>Welcome to the Guided Import Wizard</h4>
                    <p>This wizard will help you choose the best method to import your data into Galaxy.</p>
                    <!-- TODO: Add wizard steps here -->
                    <p class="text-muted">Wizard steps will go here...</p>
                </div>
            </template>
            <template v-slot:footer>
                <BButton variant="secondary" @click="showGuidedModal = false">Cancel</BButton>
                <BButton variant="primary">Next Step</BButton>
            </template>
        </GModal>

        <GModal :show.sync="showAdvancedModal" title="Advanced Import" size="large" footer>
            <template v-slot:body>
                <div class="advanced-import-content">
                    <h4>Advanced Import Interface</h4>
                    <p>Access all import options and advanced settings in one place.</p>
                    <!-- TODO: Add advanced import interface here -->
                    <p class="text-muted">Advanced import interface will go here...</p>
                </div>
            </template>
            <template v-slot:footer>
                <BButton variant="secondary" @click="showAdvancedModal = false">Cancel</BButton>
                <BButton variant="primary">Start Import</BButton>
            </template>
        </GModal>
    </div>
</template>

<style lang="scss" scoped>
@import "@/style/scss/theme/blue.scss";

.upload-panel-wrapper {
    height: 100%;
    display: flex;
    flex-direction: column;
}

.upload-method-item {
    width: 100%;
    border: 1px solid $gray-300;
    transition: all 0.2s ease;
    background-color: white;

    &:hover {
        background-color: $gray-100;
        border-color: $brand-primary;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }

    &:active {
        transform: translateY(1px);
    }
}

// .upload-method-icon {
//     min-width: 3rem;
//     display: flex;
//     align-items: center;
//     justify-content: center;
// }

// .upload-method-title {
//     font-size: 1rem;
//     color: $text-color;
// }

// .upload-method-description {
//     font-size: 0.875rem;
//     line-height: 1.4;
// }
</style>

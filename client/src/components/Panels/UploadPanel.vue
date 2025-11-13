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
    category: string;
}

const query = ref("");

const uploadMethods: UploadMethod[] = [
    {
        id: "local-file",
        name: "Upload from Computer",
        description: "Select and upload files from your local device",
        icon: faDesktop,
        category: "local",
    },
    {
        id: "paste-content",
        name: "Paste File Content",
        description: "Paste the content of a file directly",
        icon: faClipboard,
        category: "direct",
    },
    {
        id: "paste-links",
        name: "Paste Links/URLs",
        description: "Paste URLs to fetch and import data from remote sources",
        icon: faLink,
        category: "direct",
    },
    {
        id: "collection-upload",
        name: "Upload File Collection",
        description: "Upload multiple files as a collection",
        icon: faColumns,
        category: "local",
    },
    {
        id: "remote-files",
        name: "Choose Remote Files",
        description: "Select files from configured remote file sources or file repositories",
        icon: faCloud,
        category: "remote",
    },
    {
        id: "data-library",
        name: "Import from Data Library",
        description: "Select files from Galaxy's data library",
        icon: faDatabase,
        category: "library",
    },
    {
        id: "explore-zip",
        name: "Explore Compressed Zip Archive",
        description: "Browse and select files directly from a compressed zip archive either locally or remotely",
        icon: faFileArchive,
        category: "archive",
    },
    {
        id: "import-history",
        name: "Import History",
        description: "Import an entire history from a file or URL",
        icon: faHdd,
        category: "import",
    },
    {
        id: "import-workflow",
        name: "Import Workflow",
        description: "Import a workflow from a file or URL",
        icon: faSitemap,
        category: "import",
    },
];

const filteredMethods = computed(() => {
    const rawTokens = query.value.trim().split(/\s+/).filter(Boolean);
    if (rawTokens.length === 0) {
        return uploadMethods;
    }
    const tokens = rawTokens.map((token) => token.toLowerCase());
    return uploadMethods.filter((method) => {
        const searchText = `${method.name} ${method.description} ${method.category}`.toLowerCase();
        return tokens.every((token) => searchText.includes(token));
    });
});

function selectUploadMethod(method: UploadMethod) {
    // TODO: Implement the actual upload logic for each method
    console.log(`Selected upload method: ${method.id}`, method);

    // Example: You could open different modals or navigate to different views
    // based on the method selected
    switch (method.id) {
        case "local-file":
            // Open local file upload dialog
            break;
        case "paste-content":
            // Open paste file content dialog
            break;
        case "paste-links":
            // Open paste links/URLs dialog
            break;
        case "collection-upload":
            // Open collection upload dialog
            break;
        case "remote-files":
            // Open remote file browser
            break;
        case "data-library":
            // Open data library import dialog
            break;
        case "import-history":
            // Open history import dialog
            break;
        case "import-workflow":
            // Open workflow import dialog
            break;
    }
}

function openAdvancedMode() {
    // TODO: Navigate to or open the advanced upload interface
    console.log("Opening advanced upload mode...");
    // Open a more complex modal with all options
}

function openGuidedMode() {
    // TODO: Navigate to or open the guided wizard interface
    console.log("Opening guided upload wizard...");
    // Open a step-by-step wizard modal, something like a decision tree
}
</script>

<template>
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
</template>

<style lang="scss" scoped>
@import "@/style/scss/theme/blue.scss";

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

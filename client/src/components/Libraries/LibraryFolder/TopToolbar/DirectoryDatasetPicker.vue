<script setup lang="ts">
import {
    BAlert,
    BButton,
    BFormCheckbox,
    BFormCheckboxGroup,
    BFormGroup,
    BFormTextarea,
    BModal,
    BTab,
    BTabs,
} from "bootstrap-vue";
import { computed, ref, watch } from "vue";
import Multiselect from "vue-multiselect";

import { GalaxyApi } from "@/api";
import { type Option } from "@/components/Form/Elements/FormDrilldown/utilities";
import { type DetailedDatatypes, useDetailedDatatypes } from "@/composables/datatypes";
import { Toast } from "@/composables/toast";
import { useDbKeyStore } from "@/stores/dbKeyStore";

import FormDrilldown from "@/components/Form/Elements/FormDrilldown/FormDrilldown.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const auto = {
    id: "auto",
    extension: "auto",
    text: "Auto-detect",
    description: `This system will try to detect the file type automatically.
                     If your file is not detected properly as one of the known formats,
                     it most likely means that it has some format problems (e.g., different
                     number of columns on different rows). You can still coerce the system
                     to set your data to the format you think it should be.
                     You can also upload compressed files, which will automatically be decompressed`,
    descriptionUrl: "",
};

type GenomesList = { id: string; text: string }[];

type RequestData = Record<string, string | boolean>;

interface Props {
    folderId: string;
    target: "userdir" | "importdir" | "path";
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "reload"): void;
    (e: "onClose"): void;
    (e: "onSelect", items: RequestData[]): void;
}>();

const dbKeyStore = useDbKeyStore();
const { datatypes, datatypesLoading } = useDetailedDatatypes();

const activeTab = ref(0);
const importing = ref(false);
const selectedGenome = ref();
const paths = ref<string>("");
const selectedExtension = ref();
const options = ref<Option[]>([]);
const optionsLoading = ref(false);
const errorMessage = ref<string>("");
const currentValue = ref<string[]>([]);
const genomesList = ref<GenomesList>([]);
const preserveOptions = ref<string[]>([]);
const extensionsList = ref<DetailedDatatypes[]>([]);

const pathMode = computed(() => {
    return props.target === "path";
});
const filesMode = computed(() => {
    return activeTab.value === 0;
});
const title = computed(() => {
    return pathMode.value ? "Please enter paths to import" : "Please select folders or files";
});
const importDisable = computed(() => {
    if (importing.value) {
        return true;
    }

    if (pathMode.value) {
        return paths.value?.length === 0;
    }

    return currentValue.value?.length === 0;
});
const okButtonText = computed(() => {
    if (currentValue.value.length === 0) {
        return "Import";
    } else {
        return `Import ${currentValue.value.length} dataset${currentValue.value.length > 1 ? "s" : ""}`;
    }
});

async function fetchOptions() {
    optionsLoading.value = true;

    const { data, error } = await GalaxyApi().GET("/api/remote_files", {
        params: {
            query: {
                format: "jstree",
                target: props.target,
                disable: filesMode.value ? "folders" : "files",
            },
        },
    });

    options.value = mapDataToOptions(data);

    if (error) {
        console.error(error);

        errorMessage.value = "Failed to load directories";
    }

    optionsLoading.value = false;
}

function mapDataToOptions(data: any): Option[] {
    return data.map((item: any) => {
        const option: Option = {
            name: item.text,
            fullPath: item.li_attr.full_path,
            value: item.li_attr.id,
            leaf: item.type === "file",
            disabled: item.state.disabled,
            options: item.children ? mapDataToOptions(item.children) : [],
        };

        return option;
    });
}

function getFullPathById(id: string): string {
    function traverse(nodes: Option[], targetId: string): string {
        for (const node of nodes) {
            if (node.value === targetId) {
                return node.fullPath as string;
            }
            if (node.options?.length > 0) {
                const result = traverse(node.options, targetId);

                if (result) {
                    return result;
                }
            }
        }

        return "";
    }

    return traverse(options.value, id);
}

async function fetchExtAndGenomes() {
    try {
        extensionsList.value = datatypes.value;

        extensionsList.value.sort((a, b) => (a.extension > b.extension ? 1 : a.extension < b.extension ? -1 : 0));

        extensionsList.value = [auto, ...extensionsList.value];

        selectedExtension.value = auto;
    } catch (err) {
        console.error(err);
    }

    try {
        await dbKeyStore.fetchUploadDbKeys();

        genomesList.value = dbKeyStore.uploadDbKeys;

        genomesList.value.sort((a, b) => (a.id > b.id ? 1 : a.id < b.id ? -1 : 0));
    } catch (err) {
        console.error(err);
    }
}

async function onImport() {
    if (pathMode.value) {
        const tmp: string[] = paths.value.split("\n");
        const validPaths: string[] = [];

        for (let i = tmp.length - 1; i >= 0; i--) {
            var trimmed = tmp?.[i]?.trim();
            if (trimmed && trimmed?.length !== 0) {
                validPaths.push(trimmed);
            }
        }

        if (validPaths.length === 0) {
            Toast.error("Please provide a valid path");
            return;
        } else {
            importFileOrFolder(validPaths, "admin_path");
        }
    } else {
        const source = `${props.target}_${filesMode.value ? "file" : "folder"}`;
        const validPaths: string[] = currentValue.value.map((item) => getFullPathById(item));

        importFileOrFolder(validPaths, source);
    }
}

async function importFileOrFolder(validPaths: string[], source: string) {
    const items: RequestData[] = [];

    for (const path of validPaths) {
        const reqData: RequestData = {
            path: path,
            source: source,
            dbkey: selectedGenome.value,
            encoded_folder_id: props.folderId,
            link_data: preserveOptions.value.includes("link_files"),
            space_to_tab: preserveOptions.value.includes("space_to_tab"),
            to_posix_lines: preserveOptions.value.includes("to_posix_lines"),
            tag_using_filenames: preserveOptions.value.includes("tags_from_filenames"),
        };

        if (!pathMode.value) {
            reqData.file_type = selectedExtension.value.extension;
        }

        if (!filesMode.value) {
            reqData.preserve_dirs = preserveOptions.value.includes("preserve_directory_structure");
        }

        items.push(reqData);
    }

    emit("onSelect", items);
    emit("onClose");
}

watch(
    activeTab,
    () => {
        if (!pathMode.value) {
            fetchOptions();
        }
    },
    { immediate: true }
);

watch(
    () => datatypesLoading.value,
    () => {
        if (!datatypesLoading.value) {
            fetchExtAndGenomes();
        }
    }
);
</script>

<template>
    <BModal :title="title" visible scrollable content-class="directory-dataset-picker" @hide="emit('onClose')">
        <BTabs v-if="!pathMode" v-model="activeTab" fill pills>
            <BTab title="Choose Files" />

            <BTab title="Choose Folders" />
        </BTabs>

        <BAlert v-if="filesMode" show class="mt-2">
            All files you select will be imported into the current folder ignoring their folder structure.
        </BAlert>
        <BAlert v-else-if="!filesMode" show class="mt-2">
            All files within the selected folders and their sub-folders will be imported into the current folder.
        </BAlert>
        <BAlert v-else-if="pathMode" show class="mt-2">
            All files within the given folders and their sub-folders will be imported into the current folder.
        </BAlert>

        <BFormCheckboxGroup v-model="preserveOptions" switches>
            <BFormCheckbox value="link_files">Link files instead of copying </BFormCheckbox>
            <BFormCheckbox value="to_posix_lines">Convert line endings to POSIX</BFormCheckbox>
            <BFormCheckbox value="space_to_tab">Convert spaces to tabs</BFormCheckbox>
            <BFormCheckbox value="tags_from_filenames">Tag datasets based on file names</BFormCheckbox>
            <BFormCheckbox v-if="!filesMode || pathMode" value="preserve_directory_structure">
                Preserve directory structure
            </BFormCheckbox>
        </BFormCheckboxGroup>

        <hr />

        You can set extension type and genome for all imported datasets at once:
        <BFormGroup label="Genome">
            <Multiselect
                v-model="selectedGenome"
                :options="genomesList"
                label="text"
                track-by="id"
                placeholder="Select genome"
                :close-on-select="true"
                :preserve-search="true"
                :searchable="true"
                :allow-empty="true"
                :max="1" />
        </BFormGroup>

        <BFormGroup label="Extension">
            <Multiselect
                v-model="selectedExtension"
                :options="extensionsList"
                label="extension"
                track-by="id"
                placeholder="Select extension"
                :close-on-select="true"
                :preserve-search="true"
                :searchable="true"
                :allow-empty="true"
                :max="1" />
        </BFormGroup>

        <hr />

        <BFormTextarea
            v-if="pathMode"
            id="import_paths"
            v-model="paths"
            placeholder="Absolute paths (or paths relative to Galaxy root) separated by newline"
            rows="5" />

        <BAlert v-if="optionsLoading" variant="info" show>
            <LoadingSpan message="Loading directories" />
        </BAlert>
        <BAlert v-else-if="errorMessage" variant="danger" show>
            {{ errorMessage }}
        </BAlert>
        <FormDrilldown
            v-else
            :id="filesMode ? 'files' : 'folders'"
            v-model="currentValue"
            class="items-list"
            show-icons
            :options="options"
            multiple />

        <template v-slot:modal-footer>
            <BButton size="sm" variant="secondary" :disabled="importing" @click="emit('onClose')">Close</BButton>
            <BButton size="sm" variant="primary" :disabled="importDisable" @click="onImport">
                {{ okButtonText }}
            </BButton>
        </template>
    </BModal>
</template>

<style scoped lang="scss">
.directory-dataset-picker {
    display: grid;
    grid-template-rows: max-content 1fr;

    .items-list {
        max-height: 100%;
        overflow-y: auto;
    }
}
</style>

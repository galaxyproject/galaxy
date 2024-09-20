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

import { GalaxyApi } from "@/api";
import { type Option } from "@/components/Form/Elements/FormDrilldown/utilities";
import { type DetailedDatatypes, useDetailedDatatypes } from "@/composables/datatypes";
import { Toast } from "@/composables/toast";
import { useDbKeyStore } from "@/stores/dbKeyStore";

import FormDrilldown from "@/components/Form/Elements/FormDrilldown/FormDrilldown.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import SingleItemSelector from "@/components/SingleItemSelector.vue";

const autoExtension = {
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

type DbKey = { id: string; text: string };
type DbKeyList = DbKey[];

type RequestData = {
    path: string;
    source: string;
    dbkey: string;
    encoded_folder_id: string;
    file_type?: string;
    preserve_dirs?: boolean;
    link_data: boolean;
    space_to_tab: boolean;
    to_posix_lines: boolean;
    tag_using_filenames: boolean;
};

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
const paths = ref<string>("");
const options = ref<Option[]>([]);
const optionsLoading = ref(false);
const selectedDbKey = ref<DbKey>();
const dbKeyList = ref<DbKeyList>([]);
const errorMessage = ref<string>("");
const currentValue = ref<string[]>([]);
const preserveOptions = ref<string[]>([]);
const extensionsList = ref<DetailedDatatypes[]>([]);
const selectedExtension = ref<DetailedDatatypes>(autoExtension);

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
    const length = currentValue.value?.length || 0;

    return length === 0 ? "Import" : `Import ${length} dataset${length > 1 ? "s" : ""}`;
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

        errorMessage.value = "Failed to load directories: " + error?.err_msg;
    }

    optionsLoading.value = false;
}

function mapDataToOptions(data: any): Option[] {
    return data?.map((item: any) => {
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

async function fetchExtAndDbKey() {
    try {
        extensionsList.value = datatypes.value;

        extensionsList.value.sort((a, b) => (a.extension > b.extension ? 1 : a.extension < b.extension ? -1 : 0));

        extensionsList.value = [autoExtension, ...extensionsList.value];

        selectedExtension.value = autoExtension;
    } catch (err) {
        console.error(err);
    }

    try {
        await dbKeyStore.fetchUploadDbKeys();

        dbKeyList.value = dbKeyStore.uploadDbKeys as DbKeyList;

        selectedDbKey.value = dbKeyStore.uploadDbKeys.find((item: DbKey) => item.id === "?");

        dbKeyList.value.sort((a, b) => (a.id > b.id ? 1 : a.id < b.id ? -1 : 0));
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
            dbkey: selectedDbKey.value?.id || "?",
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

function onSelectDbKey(item: DbKey) {
    selectedDbKey.value = item;
}

function onSelectExtension(item: DetailedDatatypes) {
    selectedExtension.value = item;
}

watch(
    () => datatypesLoading.value,
    () => {
        if (!datatypesLoading.value) {
            fetchExtAndDbKey();
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

        <BFormCheckboxGroup v-model="preserveOptions" switches class="directory-dataset-picker-options">
            <BFormCheckbox value="link_files">Link files instead of copying </BFormCheckbox>
            <BFormCheckbox value="to_posix_lines">Convert line endings to POSIX</BFormCheckbox>
            <BFormCheckbox value="space_to_tab">Convert spaces to tabs</BFormCheckbox>
            <BFormCheckbox value="tags_from_filenames">Tag datasets based on file names</BFormCheckbox>
            <BFormCheckbox v-if="!filesMode || pathMode" value="preserve_directory_structure">
                Preserve directory structure
            </BFormCheckbox>
        </BFormCheckboxGroup>

        <hr />

        You can set database/build and extension type for all imported datasets at once:
        <BFormGroup label="Database/Build">
            <SingleItemSelector
                :current-item="selectedDbKey"
                collection-name="DB Keys"
                :items="dbKeyList"
                @update:selected-item="onSelectDbKey" />
        </BFormGroup>

        <BFormGroup label="Extension">
            <SingleItemSelector
                :current-item="selectedExtension"
                collection-name="Extensions"
                :items="extensionsList"
                track-by="extension"
                label="extension"
                @update:selected-item="onSelectExtension" />
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
            v-else-if="!optionsLoading"
            :id="filesMode ? 'files' : 'folders'"
            v-model="currentValue"
            class="directory-dataset-picker-list"
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

    .directory-dataset-picker-options {
        display: grid;
        grid-template-columns: 1fr 1fr;
    }

    .directory-dataset-picker-list {
        max-height: 100%;
        overflow-y: auto;
    }
}
</style>

<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faBook, faCaretDown, faDownload, faHome, faPlus, faTrash } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import {
    BAlert,
    BButton,
    BDropdown,
    BDropdownDivider,
    BDropdownGroup,
    BDropdownItem,
    BFormCheckbox,
} from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, reactive, ref } from "vue";

import { GalaxyApi } from "@/api";
import { Services } from "@/components/Libraries/LibraryFolder/services";
import mod_add_datasets from "@/components/Libraries/LibraryFolder/TopToolbar/add-datasets";
import { deleteSelectedItems } from "@/components/Libraries/LibraryFolder/TopToolbar/delete-selected";
import download from "@/components/Libraries/LibraryFolder/TopToolbar/download";
import mod_import_collection from "@/components/Libraries/LibraryFolder/TopToolbar/import-to-history/import-collection";
import mod_import_dataset from "@/components/Libraries/LibraryFolder/TopToolbar/import-to-history/import-dataset";
import { type SelectionItem } from "@/components/SelectionDialog/selectionTypes";
import { useConfig } from "@/composables/config";
import { type DetailedDatatypes, useDetailedDatatypes } from "@/composables/datatypes";
import { Toast } from "@/composables/toast";
import { useDbKeyStore } from "@/stores/dbKeyStore";
import { useUserStore } from "@/stores/userStore";

import FolderDetails from "@/components/Libraries/LibraryFolder/FolderDetails/FolderDetails.vue";
import LibraryBreadcrumb from "@/components/Libraries/LibraryFolder/LibraryBreadcrumb.vue";
import SearchField from "@/components/Libraries/LibraryFolder/SearchField.vue";
import HistoryDatasetPicker from "@/components/Libraries/LibraryFolder/TopToolbar/HistoryDatasetPicker.vue";
import ProgressBar from "@/components/ProgressBar.vue";

library.add(faBook, faCaretDown, faDownload, faHome, faPlus, faTrash);

type GenomesList = { id: string; text: string }[];

interface Props {
    metadata: any;
    selected: any[];
    folderId: string;
    unselected: any[];
    searchText: string;
    folderContents: any[];
    includeDeleted: boolean;
    isAllSelectedMode: boolean;
    canAddLibraryItem?: boolean;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "newFolder"): void;
    (e: "refreshTable"): void;
    (e: "fetchFolderContents"): void;
    (e: "refreshTableContent"): void;
    (e: "setBusy", value: boolean): void;
    (e: "deleteFromTable", item: any): void;
    (e: "updateSearch", value: string): void;
    (e: "update:includeDeleted", value: boolean): void;
}>();

const { config, isConfigLoaded } = useConfig();

const userStore = useUserStore();
const { isAdmin } = storeToRefs(userStore);

const { datatypes } = useDetailedDatatypes();

const dbKeyStore = useDbKeyStore();

const modalShow = ref("");
const genomesList = ref<GenomesList>([]);
const extensionsList = ref<DetailedDatatypes[]>([]);
const progress = ref(false);
const progressNote = ref("");
const progressStatus = reactive({
    total: 0,
    okCount: 0,
    errorCount: 0,
    runningCount: 0,
});
const auto = ref({
    id: "auto",
    extension: "auto",
    text: "Auto-detect",
    description: `This system will try to detect the file type automatically.
                     If your file is not detected properly as one of the known formats,
                     it most likely means that it has some format problems (e.g., different
                     number of columns on different rows). You can still coerce the system
                     to set your data to the format you think it should be.
                     You can also upload compressed files, which will automatically be decompressed`,
    description_url: "",
});

const services = new Services();

const libraryImportDir = computed(() => isConfigLoaded && config.value?.library_import_dir);
const allowLibraryPathPaste = computed(() => isConfigLoaded && config.value?.allow_library_path_paste);
const userLibraryImportDirAvailable = computed(() => isConfigLoaded && config.value?.user_library_import_dir_available);
const containsFileOrFolder = computed(() => {
    return props.folderContents.find((el) => el.type === "folder" || el.type === "file");
});
const canDelete = computed(() => {
    return !!(containsFileOrFolder.value && isAdmin.value);
});
const datasetManipulation = computed(() => {
    return !!(containsFileOrFolder.value && userStore.currentUser);
});
const totalRows = computed(() => {
    return props.metadata?.total_rows ?? 0;
});

function updateSearch(value: string) {
    emit("updateSearch", value);
}

function newFolder() {
    emit("newFolder");
}

async function getSelected() {
    if (props.isAllSelectedMode) {
        try {
            emit("setBusy", true);

            const selected = await services.getFilteredFolderContents(
                props.folderId,
                props.unselected,
                props.searchText,
                totalRows.value
            );

            emit("setBusy", false);

            return selected;
        } catch (err) {
            console.error(err);
        } finally {
            emit("setBusy", false);
        }

        return [];
    } else {
        return props.selected;
    }
}

async function deleteSelected() {
    try {
        const selected = await getSelected();

        deleteSelectedItems(
            selected,
            (deletedItem: any) => emit("deleteFromTable", deletedItem),
            () => emit("refreshTable"),
            () => emit("refreshTableContent")
        );
    } catch (err) {
        console.error(err);
    }
}

async function findCheckedItems(idOnly = true) {
    const folders: any[] = [];
    const datasets: any[] = [];

    try {
        const selected = await getSelected();

        selected.forEach((item: any) => {
            const selectedItem = idOnly ? item.id : item;

            item.type === "file" ? datasets.push(selectedItem) : folders.push(selectedItem);
        });
    } catch (err) {
        console.error(err);
    }

    return { datasets, folders };
}

async function downloadData(format: string) {
    try {
        const { datasets, folders } = await findCheckedItems();

        if (props.selected.length === 0) {
            Toast.info("You must select at least one dataset to download");

            return;
        }

        download(format, datasets, folders);
    } catch (err) {
        console.error(err);
    }
}

async function importToHistoryModal(isCollection: boolean) {
    try {
        const { datasets, folders } = await findCheckedItems(!isCollection);

        const checkedItems: any = props.selected;

        checkedItems.dataset_ids = datasets;
        checkedItems.folder_ids = folders;

        if (isCollection) {
            new mod_import_collection.ImportCollectionModal({
                selected: checkedItems,
            });
        } else {
            new mod_import_dataset.ImportDatasetModal({
                selected: checkedItems,
            });
        }
    } catch (err) {
        console.error(err);
    }
}

function onAddDatasets(source: string = "") {
    modalShow.value = source;
}

// TODO: after replacing the selection dialog with the new component that is not using jquery
async function addDatasets(source: string) {
    await fetchExtAndGenomes();

    new mod_add_datasets.AddDatasets({
        source: source,
        id: props.folderId,
        updateContent: updateContent,
        list_genomes: genomesList.value,
        list_extensions: extensionsList.value,
    });
}

function updateContent() {
    emit("fetchFolderContents");
}
// END TODO

async function fetchExtAndGenomes() {
    try {
        extensionsList.value = datatypes.value;

        extensionsList.value.sort((a, b) => (a.extension > b.extension ? 1 : a.extension < b.extension ? -1 : 0));

        extensionsList.value = [auto.value, ...extensionsList.value];
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

function resetProgress() {
    progressStatus.total = 0;
    progressStatus.okCount = 0;
    progressStatus.errorCount = 0;
    progressStatus.runningCount = 0;
}

async function onAddDatasetsFromHistory(selectedDatasets: SelectionItem[]) {
    resetProgress();

    progress.value = true;
    progressStatus.total = selectedDatasets.length;
    progressNote.value = "Adding datasets to the folder";

    emit("setBusy", true);

    for (const dataset of selectedDatasets) {
        try {
            progressStatus.runningCount++;

            const { error } = await GalaxyApi().POST("/api/folders/{folder_id}/contents", {
                params: {
                    path: { folder_id: props.folderId },
                },
                body: {
                    ldda_message: null,
                    from_hda_id: dataset.id,
                },
            });

            if (error) {
                throw new Error(error.err_msg);
            }

            progressStatus.okCount++;
        } catch (err) {
            progressStatus.errorCount++;
        } finally {
            progressStatus.runningCount--;
        }
    }

    if (progressStatus.errorCount > 0) {
        progressNote.value = `Added ${progressStatus.okCount} dataset${
            progressStatus.okCount > 1 ? "s" : ""
        }, but failed to add ${progressStatus.errorCount} dataset${
            progressStatus.errorCount > 1 ? "s" : ""
        } to the folder`;
    } else {
        progressNote.value = `Added ${progressStatus.okCount} dataset${
            progressStatus.okCount > 1 ? "s" : ""
        } to the folder`;
    }

    emit("setBusy", false);
    emit("fetchFolderContents");
}
</script>

<template>
    <div>
        <div class="form-inline d-flex align-items-center mb-2">
            <BButton
                class="mr-1 btn btn-secondary"
                :to="{ path: `/libraries` }"
                data-toggle="tooltip"
                title="Go to libraries list">
                <FontAwesomeIcon :icon="faHome" />
            </BButton>

            <div>
                <div class="form-inline">
                    <SearchField @updateSearch="updateSearch($event)"></SearchField>

                    <BButton
                        v-if="props.canAddLibraryItem"
                        title="Create new folder"
                        class="add-library-items-folder mr-1"
                        type="button"
                        @click="newFolder">
                        <FontAwesomeIcon :icon="faPlus" />
                        Folder
                    </BButton>

                    <BDropdown
                        v-if="props.canAddLibraryItem"
                        v-b-tooltip.top.noninteractive
                        right
                        no-caret
                        class="add-library-items-datasets mr-1">
                        <template v-slot:button-content>
                            <FontAwesomeIcon :icon="faPlus" />
                            Datasets
                            <FontAwesomeIcon :icon="faCaretDown" />
                        </template>

                        <BDropdownItem @click="onAddDatasets('history')"> from History </BDropdownItem>

                        <BDropdownItem v-if="userLibraryImportDirAvailable" @click="addDatasets('userdir')">
                            from User Directory
                        </BDropdownItem>

                        <BDropdownDivider v-if="libraryImportDir || allowLibraryPathPaste" />

                        <BDropdownGroup v-if="libraryImportDir || allowLibraryPathPaste" header="Admins Only">
                            <BDropdownItem v-if="libraryImportDir" @click="addDatasets('importdir')">
                                from Import Directory
                            </BDropdownItem>

                            <BDropdownItem v-if="allowLibraryPathPaste" @click="addDatasets('path')">
                                from Path
                            </BDropdownItem>
                        </BDropdownGroup>
                    </BDropdown>

                    <BDropdown v-b-tooltip.top.noninteractive right no-caret class="add-to-history mr-1">
                        <template v-slot:button-content>
                            <FontAwesomeIcon :icon="faBook" />
                            Add to History
                            <FontAwesomeIcon :icon="faCaretDown" />
                        </template>

                        <BDropdownItem class="add-to-history-datasets" @click="importToHistoryModal(false)">
                            as Datasets
                        </BDropdownItem>

                        <BDropdownItem class="add-to-history-collection" @click="importToHistoryModal(true)">
                            as a Collection
                        </BDropdownItem>
                    </BDropdown>

                    <div
                        v-if="datasetManipulation"
                        title="Download items as archive"
                        class="dropdown dataset-manipulation mr-1">
                        <BButton id="download--btn" type="button" class="primary-button" @click="downloadData('zip')">
                            <FontAwesomeIcon :icon="faDownload" />
                            Download
                        </BButton>
                    </div>

                    <BButton
                        v-if="canDelete"
                        data-toggle="tooltip"
                        title="Mark items deleted"
                        class="primary-button toolbtn-bulk-delete logged-dataset-manipulation mr-1"
                        type="button"
                        @click="deleteSelected">
                        <FontAwesomeIcon :icon="faTrash" />
                        Delete
                    </BButton>

                    <FolderDetails :id="props.folderId" class="mr-1" :metadata="props.metadata" />

                    <div v-if="canDelete" class="form-check logged-dataset-manipulation mr-1">
                        <BFormCheckbox :checked="props.includeDeleted" @change="$emit('update:includeDeleted', $event)">
                            include deleted
                        </BFormCheckbox>
                    </div>
                </div>
            </div>
        </div>

        <BAlert v-model="progress" dismissible variant="info" class="mb-1">
            <ProgressBar
                :loading="progressStatus.runningCount > 0"
                :note="progressNote"
                :total="progressStatus.total"
                :ok-count="progressStatus.okCount"
                :error-count="progressStatus.errorCount"
                :running-count="progressStatus.runningCount" />
        </BAlert>

        <LibraryBreadcrumb
            v-if="props.metadata && props.metadata.full_path"
            :full_path="props.metadata.full_path"
            :current-id="props.folderId" />

        <HistoryDatasetPicker
            v-if="modalShow === 'history'"
            :folder-id="props.folderId"
            @onSelect="onAddDatasetsFromHistory"
            @onClose="onAddDatasets" />
    </div>
</template>

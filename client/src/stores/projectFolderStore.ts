import { defineStore } from "pinia";
import { computed, ref } from "vue";

import { GalaxyApi } from "@/api";
import { rethrowSimple } from "@/utils/simple-error";

export interface ProjectFolder {
    id: string;
    name: string;
    create_time: string;
    update_time: string;
    count: number;
}

/** Sentinel for "not filtering by folder at all", as opposed to a folder id. */
export const ALL_HISTORIES = null;

export const useProjectFolderStore = defineStore("projectFolderStore", () => {
    const folders = ref<ProjectFolder[]>([]);
    const loading = ref(false);
    const loaded = ref(false);
    /** The folder currently being browsed, or null for all histories. */
    const currentFolderId = ref<string | null>(ALL_HISTORIES);

    const currentFolder = computed(() => folders.value.find((f) => f.id === currentFolderId.value) ?? null);
    const totalFiled = computed(() => folders.value.reduce((sum, f) => sum + f.count, 0));

    async function fetchFolders(force = false) {
        if (loading.value || (loaded.value && !force)) {
            return;
        }
        loading.value = true;
        try {
            const { data, error } = await GalaxyApi().GET("/api/project_folders");
            if (error) {
                // Folders are an optional aid, so a failure here must not take
                // the history list down with it: log and carry on with none.
                console.debug("Could not load project folders", error);
                return;
            }
            folders.value = (data ?? []) as ProjectFolder[];
            loaded.value = true;
        } finally {
            loading.value = false;
        }
    }

    async function createFolder(name: string) {
        const { data, error } = await GalaxyApi().POST("/api/project_folders", { body: { name } });
        if (error) {
            rethrowSimple(error);
        }
        await fetchFolders(true);
        return data as ProjectFolder;
    }

    async function renameFolder(folderId: string, name: string) {
        const { error } = await GalaxyApi().PUT("/api/project_folders/{folder_id}", {
            params: { path: { folder_id: folderId } },
            body: { name },
        });
        if (error) {
            rethrowSimple(error);
        }
        await fetchFolders(true);
    }

    async function deleteFolder(folderId: string) {
        const { error } = await GalaxyApi().DELETE("/api/project_folders/{folder_id}", {
            params: { path: { folder_id: folderId } },
        });
        if (error) {
            rethrowSimple(error);
        }
        // Deleting a folder releases its histories rather than removing them,
        // so step back to showing everything instead of an empty folder.
        if (currentFolderId.value === folderId) {
            currentFolderId.value = ALL_HISTORIES;
        }
        await fetchFolders(true);
    }

    async function setHistoryFolder(historyId: string, folderId: string | null) {
        const { error } = await GalaxyApi().PUT("/api/histories/{history_id}/project_folder", {
            params: { path: { history_id: historyId } },
            body: { project_folder_id: folderId },
        });
        if (error) {
            rethrowSimple(error);
        }
        // Counts moved, so they have to be refetched.
        await fetchFolders(true);
    }

    function setCurrentFolder(folderId: string | null) {
        currentFolderId.value = folderId;
    }

    return {
        folders,
        loading,
        loaded,
        currentFolderId,
        currentFolder,
        totalFiled,
        fetchFolders,
        createFolder,
        renameFolder,
        deleteFolder,
        setHistoryFolder,
        setCurrentFolder,
    };
});

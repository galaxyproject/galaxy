<script setup lang="ts">
import { faFolder, faFolderOpen, faPlus } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BBadge, BListGroup, BListGroupItem } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";

import { useProjectFolderStore } from "@/stores/projectFolderStore";
import localize from "@/utils/localization";

import GButton from "@/components/BaseComponents/GButton.vue";
import GModal from "@/components/BaseComponents/GModal.vue";

interface Props {
    showModal: boolean;
    /** Histories to file; the count is shown so it is clear what is affected. */
    historyIds: string[];
}
const props = withDefaults(defineProps<Props>(), { showModal: false, historyIds: () => [] });

const emit = defineEmits<{
    (e: "update:show-modal", show: boolean): void;
    (e: "filed", folderId: string | null): void;
}>();

const store = useProjectFolderStore();
const { folders } = storeToRefs(store);

const busy = ref(false);
const progress = ref(0);
const errorMessage = ref("");
const creating = ref(false);
const newName = ref("");

const propShowModal = computed({
    get: () => props.showModal,
    set: (value: boolean) => emit("update:show-modal", value),
});

const title = computed(() =>
    props.historyIds.length === 1
        ? localize("Add history to folder")
        : `${localize("Add")} ${props.historyIds.length} ${localize("histories to folder")}`,
);

watch(
    () => props.showModal,
    (show) => {
        if (show) {
            errorMessage.value = "";
            progress.value = 0;
            store.fetchFolders();
        }
    },
);

async function chooseFolder(folderId: string | null) {
    busy.value = true;
    errorMessage.value = "";
    progress.value = 0;
    try {
        // One at a time: this can be a large selection, and firing every
        // request at once would bury the server.
        for (const historyId of props.historyIds) {
            await store.setHistoryFolder(historyId, folderId);
            progress.value += 1;
        }
        emit("filed", folderId);
        propShowModal.value = false;
    } catch (error) {
        errorMessage.value = String(error);
    } finally {
        busy.value = false;
    }
}

async function createAndChoose() {
    const name = newName.value.trim();
    if (!name) {
        return;
    }
    busy.value = true;
    try {
        const folder = await store.createFolder(name);
        newName.value = "";
        creating.value = false;
        busy.value = false;
        await chooseFolder(folder.id);
    } catch (error) {
        errorMessage.value = String(error);
        busy.value = false;
    }
}
</script>

<template>
    <GModal :show.sync="propShowModal" size="small" :title="title">
        <div v-if="errorMessage" class="alert alert-danger" role="alert">{{ errorMessage }}</div>

        <BListGroup v-if="folders.length">
            <BListGroupItem
                v-for="folder in folders"
                :key="folder.id"
                button
                :disabled="busy"
                :data-folder-id="folder.id"
                class="d-flex justify-content-between align-items-center"
                @click="chooseFolder(folder.id)">
                <span><FontAwesomeIcon :icon="faFolder" class="mr-2" />{{ folder.name }}</span>
                <BBadge pill>{{ folder.count }}</BBadge>
            </BListGroupItem>
            <BListGroupItem button :disabled="busy" data-description="remove from folder" @click="chooseFolder(null)">
                <FontAwesomeIcon :icon="faFolderOpen" class="mr-2" />
                {{ localize("No folder (unfile)") }}
            </BListGroupItem>
        </BListGroup>

        <p v-else class="text-muted">
            {{ localize("No project folders yet. Create one below.") }}
        </p>

        <div class="mt-2">
            <GButton v-if="!creating" size="small" transparent :disabled="busy" @click="creating = true">
                <FontAwesomeIcon :icon="faPlus" class="mr-1" />
                {{ localize("New folder") }}
            </GButton>
            <div v-else class="d-flex align-items-center">
                <input
                    v-model="newName"
                    class="form-control form-control-sm mr-1"
                    :placeholder="localize('Folder name')"
                    :disabled="busy"
                    @keyup.enter="createAndChoose"
                    @keyup.esc="creating = false" />
                <GButton size="small" color="blue" :disabled="busy || !newName.trim()" @click="createAndChoose">
                    {{ localize("Create and add") }}
                </GButton>
            </div>
        </div>

        <p v-if="busy" class="text-muted small mt-2">
            {{ localize("Filing") }} {{ progress }} / {{ props.historyIds.length }}...
        </p>
    </GModal>
</template>

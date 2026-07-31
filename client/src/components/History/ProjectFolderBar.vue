<script setup lang="ts">
import { faFolder, faFolderOpen, faPlus } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BBadge } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, onMounted, ref } from "vue";

import { useProjectFolderStore } from "@/stores/projectFolderStore";
import localize from "@/utils/localization";

import GButton from "@/components/BaseComponents/GButton.vue";

interface Props {
    /** Total histories the user can see, for the "all histories" count. */
    totalCount?: number;
}
const props = withDefaults(defineProps<Props>(), { totalCount: 0 });

const emit = defineEmits<{
    (e: "change", folderId: string | null): void;
}>();

const store = useProjectFolderStore();
const { folders, currentFolderId, loading } = storeToRefs(store);

const creating = ref(false);
const newName = ref("");

/** Folders are opt-in: with none created the bar stays out of the way. */
const hasFolders = computed(() => folders.value.length > 0);

onMounted(() => store.fetchFolders());

function select(folderId: string | null) {
    store.setCurrentFolder(folderId);
    emit("change", folderId);
}

async function create() {
    const name = newName.value.trim();
    if (!name) {
        return;
    }
    await store.createFolder(name);
    newName.value = "";
    creating.value = false;
}
</script>

<template>
    <div class="project-folder-bar">
        <div class="d-flex flex-wrap align-items-center gap-1">
            <GButton
                size="small"
                :transparent="currentFolderId !== null"
                :color="currentFolderId === null ? 'blue' : undefined"
                data-description="all histories"
                @click="select(null)">
                <FontAwesomeIcon :icon="faFolderOpen" class="mr-1" />
                {{ localize("All histories") }}
                <BBadge v-if="props.totalCount" pill class="ml-1">{{ props.totalCount }}</BBadge>
            </GButton>

            <GButton
                v-for="folder in folders"
                :key="folder.id"
                size="small"
                :transparent="currentFolderId !== folder.id"
                :color="currentFolderId === folder.id ? 'blue' : undefined"
                :data-folder-id="folder.id"
                @click="select(folder.id)">
                <FontAwesomeIcon :icon="faFolder" class="mr-1" />
                {{ folder.name }}
                <BBadge pill class="ml-1">{{ folder.count }}</BBadge>
            </GButton>

            <GButton
                v-if="!creating"
                size="small"
                transparent
                :title="localize('Create a project folder')"
                tooltip
                data-description="new project folder"
                @click="creating = true">
                <FontAwesomeIcon :icon="faPlus" />
            </GButton>

            <span v-else class="d-flex align-items-center">
                <input
                    v-model="newName"
                    class="form-control form-control-sm mr-1"
                    :placeholder="localize('Folder name')"
                    @keyup.enter="create"
                    @keyup.esc="creating = false" />
                <GButton size="small" color="blue" :disabled="!newName.trim()" @click="create">
                    {{ localize("Create") }}
                </GButton>
            </span>
        </div>

        <div v-if="!hasFolders && !loading" class="text-muted small mt-1">
            {{ localize("Group histories into project folders to browse them one project at a time.") }}
        </div>
    </div>
</template>

<style scoped lang="scss">
.project-folder-bar {
    .gap-1 {
        gap: 0.25rem;
    }
}
</style>

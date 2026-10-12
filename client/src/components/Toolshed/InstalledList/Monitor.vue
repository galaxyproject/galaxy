<script setup lang="ts">
import { computed, onUnmounted, ref } from "vue";

import type { TableField } from "@/components/Common/GTable.types";
import { Services } from "@/components/Toolshed/services";
import { useResourceWatcher } from "@/composables/resourceWatcher";

import GAlert from "@/components/BaseComponents/GAlert.vue";
import GLink from "@/components/BaseComponents/GLink.vue";
import GCard from "@/components/Common/GCard.vue";
import GTable from "@/components/Common/GTable.vue";
import InstallationActions from "@/components/Toolshed/RepositoryDetails/InstallationActions.vue";

const POLL_DELAY = 5000;

// Full API row: uninstallRepository sends every field as a query param.
interface InstallingRepository {
    name: string;
    owner: string;
    status: string;
    [key: string]: unknown;
}

const emit = defineEmits<{
    (e: "onQuery", query: string): void;
}>();

const services = new Services();

const loading = ref(true);
const error = ref<unknown>(null);
const items = ref<InstallingRepository[]>([]);

const fields: TableField[] = [
    {
        key: "name",
        label: "Name",
    },
    {
        key: "status",
        label: "Status",
    },
    {
        key: "actions",
        label: "Actions",
    },
];

const showItems = computed(() => items.value.length > 0);

const showEmpty = computed(() => !loading.value && items.value.length === 0);

const { startWatchingResource, dispose } = useResourceWatcher(load, {
    shortPollingInterval: POLL_DELAY,
    enableBackgroundPolling: false,
});

async function load() {
    try {
        items.value = await services.getInstalledRepositories({
            filter: (x: InstallingRepository) => x.status !== "Installed",
        });
        loading.value = false;
    } catch (e) {
        error.value = e;
        dispose();
    }
}

function onQuery(q: string) {
    emit("onQuery", q);
}

function uninstallRepository(repository: InstallingRepository) {
    services.uninstallRepository(repository).catch((e: unknown) => {
        error.value = e;
    });
}

startWatchingResource();

onUnmounted(dispose);
</script>

<template>
    <div>
        <GAlert v-if="error" variant="danger" show>
            {{ error }}
        </GAlert>

        <GCard v-if="showItems" class="my-2">
            <h2 class="m-3 h-text">Currently installing...</h2>

            <GTable :items="items" :fields="fields" hide-header class="m-2">
                <template v-slot:cell(name)="row">
                    <GLink tooltip title="Show all repositories with this name" @click="onQuery(row.item.name)">
                        {{ row.item.name }} ({{ row.item.owner }})
                    </GLink>
                </template>

                <template v-slot:cell(status)="row">
                    <b>Status: </b><span>{{ row.item.status }}</span>
                </template>

                <template v-slot:cell(actions)="row">
                    <InstallationActions
                        class="float-right"
                        :status="row.item.status"
                        @onUninstall="uninstallRepository(row.item)" />
                </template>
            </GTable>
        </GCard>

        <GAlert v-if="showEmpty" variant="info" show> Currently there are no installing repositories. </GAlert>
    </div>
</template>

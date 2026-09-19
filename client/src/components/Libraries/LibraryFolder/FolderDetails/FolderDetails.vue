<script setup lang="ts">
import { faInfoCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { ref } from "vue";

import { getLibrary, type LibraryFolderMetadata, type LibrarySummary } from "@/api/libraries";
import { buildFields } from "@/components/Libraries/library-utils";
import _l from "@/utils/localization";
import { errorMessageAsString } from "@/utils/simple-error";

import GAlert from "@/components/BaseComponents/GAlert.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import GModal from "@/components/BaseComponents/GModal.vue";
import GTable from "@/components/Common/GTable.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import UtcDate from "@/components/UtcDate.vue";

// Types
type FieldEntry = { name: string; value: string };

// Constants
const DETAILS_CAPTION = _l("Details");
const FOLDER_HEADER = _l("Folder");
const LIBRARY_HEADER = _l("Library");
const TITLE_LOCATION_DETAILS = _l("Location Details");

const FIELDS = [
    {
        key: "name",
        label: _l("Name"),
        class: "name-column",
    },
    {
        key: "value",
        label: _l("Value"),
    },
];

const FOLDER_FIELD_TITLES = {
    folder_name: _l("Name"),
    folder_description: _l("Description"),
    id: "ID",
} as const satisfies Partial<Record<keyof LibraryFolderMetadata | "id", string>>;

const LIBRARY_FIELD_TITLES = {
    name: _l("Name"),
    description: _l("Description"),
    synopsis: _l("Synopsis"),
    create_time_pretty: _l("Created"),
    id: "ID",
} as const satisfies Partial<Record<keyof LibrarySummary, string>>;

// Props
const props = defineProps<{
    id: string;
    metadata: LibraryFolderMetadata;
}>();

const showModal = ref(false);

const libraryDetails = ref<FieldEntry[] | null>(null);

const folderDetails = ref<FieldEntry[] | null>(null);

const error = ref<string | null>(null);
const fetchingDetails = ref(false);

async function retrieveLibraryDetails() {
    try {
        fetchingDetails.value = true;
        error.value = null;
        const data = await getLibrary(props.metadata.parent_library_id);
        return buildFields(LIBRARY_FIELD_TITLES, data) as FieldEntry[];
    } catch (e) {
        error.value = `${_l("Failed to retrieve library details.")} ${errorMessageAsString(e)}`;
        return null;
    } finally {
        fetchingDetails.value = false;
    }
}

async function getDetails() {
    // Compose the folder metadata with it's id as a new object
    const folderData = { ...props.metadata, id: props.id };
    folderDetails.value = buildFields(FOLDER_FIELD_TITLES, folderData) as FieldEntry[];
    libraryDetails.value = await retrieveLibraryDetails();
}
</script>

<template>
    <div>
        <GButton
            size="medium"
            class="details-btn"
            title="Show location details"
            data-testid="loc-details-btn"
            @click="showModal = true">
            <FontAwesomeIcon :icon="faInfoCircle" />
            {{ DETAILS_CAPTION }}
        </GButton>

        <GModal
            id="details-modal"
            size="small"
            :show.sync="showModal"
            :title="TITLE_LOCATION_DETAILS"
            @open="getDetails">
            <div>
                <GAlert :show="Boolean(error)" variant="danger" data-testid="error-alert">
                    {{ error }}
                </GAlert>

                <div v-if="libraryDetails">
                    <GTable
                        caption-top
                        compact
                        hide-header
                        striped
                        :fields="FIELDS"
                        :items="libraryDetails"
                        data-testid="library-table">
                        <template v-slot:table-caption>
                            <h2 class="h-sm">
                                <b>{{ LIBRARY_HEADER }}</b>
                            </h2>
                        </template>
                    </GTable>
                </div>
                <GAlert v-else-if="fetchingDetails">
                    <LoadingSpan :message="_l('Retrieving library details')" />
                </GAlert>

                <div v-if="folderDetails">
                    <GTable
                        caption-top
                        compact
                        hide-header
                        striped
                        :fields="FIELDS"
                        :items="folderDetails"
                        data-testid="folder-table">
                        <template v-slot:table-caption>
                            <h2 class="h-sm">
                                <b>{{ FOLDER_HEADER }}</b>
                            </h2>
                        </template>

                        <template v-slot:cell(value)="row">
                            <div v-if="row.item.name === LIBRARY_FIELD_TITLES.create_time_pretty">
                                <UtcDate :date="row.item.value" mode="elapsed" />
                            </div>
                            <div v-else>{{ row.item.value }}</div>
                        </template>
                    </GTable>
                </div>
            </div>
        </GModal>
    </div>
</template>

<style>
/* Cannot be scoped because name-column is used in tdClass */
.name-column {
    width: 25%;
}
</style>

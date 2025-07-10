<script setup lang="ts">
import {
    faArchive,
    faBars,
    faBurn,
    faColumns,
    faCopy,
    faExchangeAlt,
    faFileArchive,
    faFileExport,
    faList,
    faPlay,
    faPlus,
    faSpinner,
    faStream,
    faTrash,
    faUsersCog,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import axios from "axios";
import {
    BButton,
    BButtonGroup,
    BDropdown,
    BDropdownDivider,
    BDropdownItem,
    BDropdownText,
    BFormCheckbox,
    BModal,
    BSpinner,
} from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";

import { canMutateHistory, type HistorySummary } from "@/api";
import { iframeRedirect } from "@/components/plugins/legacyNavigation";
import { useToast } from "@/composables/toast";
import { getAppRoot } from "@/onload/loadConfig";
import { useHistoryStore } from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";
import localize from "@/utils/localization";
import { rethrowSimple } from "@/utils/simple-error";

import CopyModal from "@/components/History/Modals/CopyModal.vue";
import SelectorModal from "@/components/History/Modals/SelectorModal.vue";

interface Props {
    histories: HistorySummary[];
    history: HistorySummary;
    historiesLoading?: boolean;
    minimal?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    historiesLoading: false,
    minimal: false,
});

// modal refs
const showSwitchModal = ref(false);
const showDeleteModal = ref(false);
const showCopyModal = ref(false);

const purgeHistory = ref(false);

const toast = useToast();

const userStore = useUserStore();
const historyStore = useHistoryStore();

const { isAnonymous } = storeToRefs(userStore);
const { totalHistoryCount, changingCurrentHistory } = storeToRefs(historyStore);

const canEditHistory = computed(() => {
    return canMutateHistory(props.history);
});

const isDeletedNotPurged = computed(() => {
    return props.history.deleted && !props.history.purged;
});

const historyState = computed(() => {
    if (props.history.purged) {
        return "purged";
    } else if (props.history.deleted) {
        return "deleted";
    } else if (props.history.archived) {
        return "archived";
    } else {
        return "active";
    }
});

function onDelete() {
    if (purgeHistory.value) {
        historyStore.deleteHistory(props.history.id, true);
    } else {
        historyStore.deleteHistory(props.history.id, false);
    }
}

function userTitle(title: string) {
    if (isAnonymous.value) {
        return localize("Log in to") + " " + localize(title);
    } else {
        return localize(title);
    }
}

async function resumePausedJobs() {
    const url = `${getAppRoot()}history/resume_paused_jobs?current=True`;
    try {
        const response = await axios.get(url);
        toast.success(response.data.message);
    } catch (e) {
        rethrowSimple(e);
    }
}
</script>

<template>
    <div>
        <nav
            :class="{ 'd-flex justify-content-between mx-3 my-2': !props.minimal }"
            aria-label="current history management">
            <h2 v-if="!props.minimal" class="m-1 h-sm">History</h2>

            <BButtonGroup>
                <BButton
                    v-if="!props.minimal"
                    v-b-tooltip.top.hover.noninteractive
                    class="create-hist-btn"
                    data-description="create new history"
                    size="sm"
                    variant="link"
                    :disabled="isAnonymous"
                    :title="userTitle('Create new history')"
                    @click="historyStore.createNewHistory">
                    <FontAwesomeIcon fixed-width :icon="faPlus" />
                </BButton>

                <BButton
                    v-if="!props.minimal"
                    v-b-tooltip.top.hover.noninteractive
                    data-description="switch to another history"
                    size="sm"
                    variant="link"
                    :disabled="isAnonymous || changingCurrentHistory"
                    :title="userTitle('Switch to history')"
                    @click="showSwitchModal = !showSwitchModal">
                    <FontAwesomeIcon
                        fixed-width
                        :icon="changingCurrentHistory ? faSpinner : faExchangeAlt"
                        :spin="changingCurrentHistory" />
                </BButton>

                <BDropdown
                    v-b-tooltip.top.hover.noninteractive
                    no-caret
                    size="sm"
                    :variant="props.minimal ? 'outline-info' : 'link'"
                    toggle-class="text-decoration-none"
                    menu-class="history-options-button-menu"
                    :title="userTitle('History options')"
                    right
                    data-description="history options">
                    <template v-slot:button-content>
                        <FontAwesomeIcon fixed-width :icon="faBars" />
                        <span class="sr-only">History Options</span>
                    </template>

                    <BDropdownText>
                        <div v-if="historiesLoading">
                            <BSpinner v-if="historiesLoading" small />
                            <span>Fetching histories from server</span>
                        </div>

                        <span v-else-if="!props.minimal">{{ localize("You have") }} {{ totalHistoryCount }} {{ localize('histories') }}.</span>
                        <span v-else>Manage History</span>
                    </BDropdownText>

                    <BDropdownItem
                        v-if="!props.minimal"
                        data-description="switch to multi history view"
                        :disabled="isAnonymous"
                        :title="userTitle('Open History Multiview')"
                        @click="$router.push('/histories/view_multiple')">
                        <FontAwesomeIcon fixed-width class="mr-1" :icon="faColumns" />
                        <span v-localize>Show Histories Side-by-Side</span>
                    </BDropdownItem>

                    <BDropdownDivider v-if="!props.minimal" />

                    <BDropdownText v-if="!canEditHistory">
                        This history has been <span class="font-weight-bold">{{ historyState }}</span
                        >.
                        <span v-localize>Some actions might not be available.</span>
                    </BDropdownText>

                    <BDropdownDivider v-if="!canEditHistory" />

                    <BDropdownItem
                        :disabled="!canEditHistory"
                        :title="localize('Resume all Paused Jobs in this History')"
                        @click="resumePausedJobs()">
                        <FontAwesomeIcon fixed-width :icon="faPlay" class="mr-1" />
                        <span v-localize>Resume Paused Jobs</span>
                    </BDropdownItem>

                    <BDropdownDivider />

                    <BDropdownItem
                        :disabled="isAnonymous"
                        :title="userTitle('Copy History to a New History')"
                        @click="showCopyModal = !showCopyModal">
                        <FontAwesomeIcon fixed-width :icon="faCopy" class="mr-1" />
                        <span v-localize>Copy this History</span>
                    </BDropdownItem>

                    <BDropdownItem
                        :disabled="!canEditHistory"
                        :title="localize(isDeletedNotPurged ? 'Permanently Delete History' : 'Delete History')"
                        @click="showDeleteModal = !showDeleteModal">
                        <FontAwesomeIcon fixed-width :icon="isDeletedNotPurged ? faBurn : faTrash" class="mr-1" />
                        <span v-if="isDeletedNotPurged" v-localize>Permanently Delete History</span>
                        <span v-else v-localize>Delete this History</span>
                    </BDropdownItem>

                    <BDropdownItem
                        :title="localize('Export references for all Tools used in this History')"
                        @click="$router.push(`/histories/citations?id=${history.id}`)">
                        <FontAwesomeIcon fixed-width :icon="faStream" class="mr-1" />
                        <span v-localize>Export Tool References</span>
                    </BDropdownItem>

                    <BDropdownItem
                        data-description="export to file"
                        :disabled="history.purged"
                        :title="localize('Export and Download History as a File')"
                        @click="$router.push(`/histories/${history.id}/export`)">
                        <FontAwesomeIcon fixed-width :icon="faFileArchive" class="mr-1" />
                        <span v-localize>Export History to File</span>
                    </BDropdownItem>

                    <BDropdownItem
                        :disabled="isAnonymous || history.archived || history.purged"
                        data-description="archive history"
                        :title="userTitle('Archive this History')"
                        @click="$router.push(`/histories/${history.id}/archive`)">
                        <FontAwesomeIcon fixed-width :icon="faArchive" class="mr-1" />
                        <span v-localize>Archive History</span>
                    </BDropdownItem>

                    <BDropdownItem
                        :disabled="isAnonymous"
                        :title="userTitle('Convert History to Workflow')"
                        @click="iframeRedirect(`/workflow/build_from_current_history?history_id=${history.id}`)">
                        <FontAwesomeIcon fixed-width :icon="faFileExport" class="mr-1" />
                        <span v-localize>Extract Workflow</span>
                    </BDropdownItem>

                    <BDropdownItem
                        :disabled="isAnonymous"
                        :title="userTitle('Display Workflow Invocations')"
                        @click="$router.push(`/histories/${history.id}/invocations`)">
                        <FontAwesomeIcon fixed-width :icon="faList" class="mr-1" />
                        <span v-localize>Show Invocations</span>
                    </BDropdownItem>

                    <BDropdownDivider />

                    <BDropdownItem
                        :disabled="isAnonymous || !canEditHistory"
                        data-description="share and manage access"
                        :title="userTitle('Share, Publish, or Set Permissions for this History')"
                        @click="$router.push(`/histories/sharing?id=${history.id}`)">
                        <FontAwesomeIcon fixed-width :icon="faUsersCog" class="mr-1" />
                        <span v-localize>Share & Manage Access</span>
                    </BDropdownItem>
                </BDropdown>
            </BButtonGroup>
        </nav>

        <SelectorModal
            v-if="!props.minimal"
            id="selector-history-modal"
            :histories="histories"
            :additional-options="['center', 'multi']"
            :show-modal.sync="showSwitchModal"
            @selectHistory="historyStore.setCurrentHistory($event.id)" />

        <CopyModal :history="history" :show-modal.sync="showCopyModal" />

        <BModal
            v-model="showDeleteModal"
            :title="isDeletedNotPurged ? 'Permanently Delete History?' : 'Delete History?'"
            title-tag="h2"
            @ok="onDelete"
            @show="purgeHistory = isDeletedNotPurged">
            <p v-localize>
                Do you also want to permanently delete the history <i class="ml-1">{{ history.name }}</i>
            </p>
            <BFormCheckbox id="purge-history" v-model="purgeHistory" :disabled="isDeletedNotPurged">
                <span v-localize>Yes, permanently delete this history.</span>
            </BFormCheckbox>
        </BModal>
    </div>
</template>

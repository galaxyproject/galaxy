<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import {
    faArchive,
    faBars,
    faColumns,
    faCopy,
    faExchangeAlt,
    faFileArchive,
    faFileExport,
    faList,
    faLock,
    faPlay,
    faPlus,
    faShareAlt,
    faStream,
    faTrash,
    faUserLock,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
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
import { useHistoryStore } from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";
import localize from "@/utils/localization";

import CopyModal from "@/components/History/Modals/CopyModal.vue";
import SelectorModal from "@/components/History/Modals/SelectorModal.vue";

library.add(
    faArchive,
    faBars,
    faColumns,
    faCopy,
    faExchangeAlt,
    faFileArchive,
    faFileExport,
    faLock,
    faPlay,
    faPlus,
    faShareAlt,
    faList,
    faStream,
    faTrash,
    faUserLock
);

interface Props {
    histories: HistorySummary[];
    history: HistorySummary;
    title?: string;
    historiesLoading?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    title: "Histories",
    historiesLoading: false,
});

const showSwitchModal = ref(false);
const purgeHistory = ref(false);

const userStore = useUserStore();
const historyStore = useHistoryStore();

const { isAnonymous } = storeToRefs(userStore);
const { totalHistoryCount } = storeToRefs(historyStore);

const canEditHistory = computed(() => {
    return canMutateHistory(props.history);
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
</script>

<template>
    <div>
        <nav class="d-flex justify-content-between mx-3 my-2" aria-label="current history management">
            <h2 class="m-1 h-sm">History</h2>

            <BButtonGroup>
                <BButton
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
                    v-b-tooltip.top.hover.noninteractive
                    data-description="switch to another history"
                    size="sm"
                    variant="link"
                    :disabled="isAnonymous"
                    :title="userTitle('Switch to history')"
                    @click="showSwitchModal = !showSwitchModal">
                    <FontAwesomeIcon fixed-width :icon="faExchangeAlt" />
                </BButton>

                <BDropdown
                    v-b-tooltip.top.hover.noninteractive
                    no-caret
                    size="sm"
                    variant="link"
                    toggle-class="text-decoration-none"
                    menu-class="history-options-button-menu"
                    title="History options"
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

                        <span v-else>You have {{ totalHistoryCount }} histories.</span>
                    </BDropdownText>

                    <BDropdownItem
                        data-description="switch to multi history view"
                        :disabled="isAnonymous"
                        :title="userTitle('Open History Multiview')"
                        @click="$router.push('/histories/view_multiple')">
                        <FontAwesomeIcon fixed-width class="mr-1" :icon="faColumns" />
                        <span v-localize>Show Histories Side-by-Side</span>
                    </BDropdownItem>

                    <BDropdownDivider />

                    <BDropdownItem
                        :disabled="!canEditHistory"
                        :title="localize('Resume all Paused Jobs in this History')"
                        @click="iframeRedirect('/history/resume_paused_jobs?current=True')">
                        <FontAwesomeIcon fixed-width :icon="faPlay" class="mr-1" />
                        <span v-localize>Resume Paused Jobs</span>
                    </BDropdownItem>

                    <BDropdownDivider />

                    <BDropdownItem
                        v-b-modal:copy-current-history-modal
                        :disabled="isAnonymous"
                        :title="userTitle('Copy History to a New History')">
                        <FontAwesomeIcon fixed-width :icon="faCopy" class="mr-1" />
                        <span v-localize>Copy this History</span>
                    </BDropdownItem>

                    <BDropdownItem v-b-modal:delete-history-modal :title="localize('Permanently Delete History')">
                        <FontAwesomeIcon fixed-width :icon="faTrash" class="mr-1" />
                        <span v-localize>Delete this History</span>
                    </BDropdownItem>

                    <BDropdownItem
                        :title="localize('Export Citations for all Tools used in this History')"
                        @click="$router.push(`/histories/citations?id=${history.id}`)">
                        <FontAwesomeIcon fixed-width :icon="faStream" class="mr-1" />
                        <span v-localize>Export Tool Citations</span>
                    </BDropdownItem>

                    <BDropdownItem
                        data-description="export to file"
                        :title="localize('Export and Download History as a File')"
                        @click="$router.push(`/histories/${history.id}/export`)">
                        <FontAwesomeIcon fixed-width :icon="faFileArchive" class="mr-1" />
                        <span v-localize>Export History to File</span>
                    </BDropdownItem>

                    <BDropdownItem
                        :disabled="isAnonymous || history.archived"
                        data-description="archive history"
                        :title="userTitle('Archive this History')"
                        @click="$router.push(`/histories/${history.id}/archive`)">
                        <FontAwesomeIcon fixed-width :icon="faArchive" class="mr-1" />
                        <span v-localize>Archive History</span>
                    </BDropdownItem>

                    <BDropdownItem
                        :disabled="isAnonymous"
                        :title="userTitle('Convert History to Workflow')"
                        @click="iframeRedirect('/workflow/build_from_current_history')">
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
                        :title="userTitle('Share or Publish this History')"
                        data-description="share or publish"
                        @click="$router.push(`/histories/sharing?id=${history.id}`)">
                        <FontAwesomeIcon fixed-width :icon="faShareAlt" class="mr-1" />
                        <span v-localize>Share or Publish</span>
                    </BDropdownItem>

                    <BDropdownItem
                        :disabled="isAnonymous || !canEditHistory"
                        :title="userTitle('Set who can View or Edit this History')"
                        @click="$router.push(`/histories/permissions?id=${history.id}`)">
                        <FontAwesomeIcon fixed-width :icon="faUserLock" class="mr-1" />
                        <span v-localize>Set Permissions</span>
                    </BDropdownItem>

                    <BDropdownItem
                        v-b-modal:history-privacy-modal
                        :disabled="isAnonymous || !canEditHistory"
                        :title="userTitle('Make this History Private')">
                        <FontAwesomeIcon fixed-width :icon="faLock" class="mr-1" />
                        <span v-localize>Make Private</span>
                    </BDropdownItem>
                </BDropdown>
            </BButtonGroup>
        </nav>

        <SelectorModal
            v-show="showSwitchModal"
            id="selector-history-modal"
            :histories="histories"
            :additional-options="['center', 'multi']"
            :show-modal.sync="showSwitchModal"
            @selectHistory="historyStore.setCurrentHistory($event.id)" />

        <CopyModal id="copy-current-history-modal" :history="history" />

        <BModal
            id="history-privacy-modal"
            title="Make History Private"
            title-tag="h2"
            @ok="historyStore.secureHistory(history)">
            <p v-localize>
                This will make all the data in this history private (excluding library datasets), and will set
                permissions such that all new data is created as private. Any datasets within that are currently shared
                will need to be re-shared or published. Are you sure you want to do this?
            </p>
        </BModal>

        <BModal
            id="delete-history-modal"
            title="Delete History?"
            title-tag="h2"
            @ok="onDelete"
            @show="purgeHistory = false">
            <p v-localize>
                Do you also want to permanently delete the history <i class="ml-1">{{ history.name }}</i>
            </p>
            <BFormCheckbox id="purge-history" v-model="purgeHistory">
                <span v-localize>Yes, permanently delete this history.</span>
            </BFormCheckbox>
        </BModal>
    </div>
</template>

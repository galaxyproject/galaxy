<!-- menu allowing user to change the current history, make a new one, basically anything that's
"above" editing the current history -->

<template>
    <div>
        <nav class="d-flex justify-content-between mx-3 my-2" aria-label="current history management">
            <h2 class="m-1 h-sm">History</h2>
            <GButtonGroup>
                <GButton
                    v-b-tooltip.bottom.hover
                    class="create-hist-btn"
                    data-description="create new history"
                    size="sm"
                    variant="link"
                    :disabled="isAnonymous"
                    :title="userTitle('Create new history')"
                    @click="createNewHistory">
                    <Icon fixed-width icon="plus" />
                </GButton>

                <GButton
                    v-b-tooltip.bottom.hover
                    data-description="switch to another history"
                    size="sm"
                    variant="link"
                    :disabled="isAnonymous"
                    :title="userTitle('Switch to history')"
                    @click="showSwitchModal = !showSwitchModal">
                    <Icon fixed-width icon="exchange-alt" />
                </GButton>

                <GDropdown
                    v-b-tooltip.bottom.hover
                    size="sm"
                    variant="link"
                    toggle-class="text-decoration-none"
                    menu-class="history-options-button-menu"
                    title="History options"
                    data-description="history options">
                    <template v-slot:button-content>
                        <span class="sr-only">History Options</span>
                    </template>
                    <GDropdownText>
                        <div v-if="historiesLoading">
                            <GSpinner v-if="historiesLoading" small />
                            <span>Fetching histories from server</span>
                        </div>
                        <span v-else>You have {{ totalHistoryCount }} histories.</span>
                    </GDropdownText>

                    <GDropdownItem
                        id="dropdown-item"
                        class="dropdown-item"
                        data-description="switch to multi history view"
                        :disabled="isAnonymous"
                        :title="userTitle('Open History Multiview')"
                        @click="$router.push('/histories/view_multiple')">
                        <Icon fixed-width class="mr-1" icon="columns" />
                        <span v-localize>Show Histories Side-by-Side</span>
                    </GDropdownItem>

                    <GDropdownDivider />

                    <GDropdownItem
                        :title="l('Resume all Paused Jobs in this History')"
                        class="dropdown-item"
                        @click="iframeRedirect('/history/resume_paused_jobs?current=True')">
                        <Icon fixed-width icon="play" class="mr-1" />
                        <span v-localize>Resume Paused Jobs</span>
                    </GDropdownItem>

                    <GDropdownDivider />

                    <GDropdownItem
                        v-b-modal:copy-current-history-modal
                        class="dropdown-item"
                        :disabled="isAnonymous"
                        :title="userTitle('Copy History to a New History')">
                        <Icon fixed-width icon="copy" class="mr-1" />
                        <span v-localize>Copy this History</span>
                    </GDropdownItem>

                    <GDropdownItem
                        v-b-modal:delete-history-modal
                        class="dropdown-item"
                        :title="l('Permanently Delete History')">
                        <Icon fixed-width icon="trash" class="mr-1" />
                        <span v-localize>Delete this History</span>
                    </GDropdownItem>

                    <GDropdownItem
                        :title="l('Export Citations for all Tools used in this History')"
                        class="dropdown-item"
                        @click="$router.push(`/histories/citations?id=${history.id}`)">
                        <Icon fixed-width icon="stream" class="mr-1" />
                        <span v-localize>Export Tool Citations</span>
                    </GDropdownItem>

                    <GDropdownItem
                        data-description="export to file"
                        class="dropdown-item"
                        :title="l('Export and Download History as a File')"
                        @click="$router.push(`/histories/${history.id}/export`)">
                        <Icon fixed-width icon="file-archive" class="mr-1" />
                        <span v-localize>Export History to File</span>
                    </GDropdownItem>

                    <GDropdownItem
                        :disabled="isAnonymous"
                        class="dropdown-item"
                        data-description="archive history"
                        :title="userTitle('Archive this History')"
                        @click="$router.push(`/histories/${history.id}/archive`)">
                        <Icon fixed-width icon="archive" class="mr-1" />
                        <span v-localize>Archive History</span>
                    </GDropdownItem>

                    <GDropdownItem
                        :disabled="isAnonymous"
                        class="dropdown-item"
                        :title="userTitle('Convert History to Workflow')"
                        @click="iframeRedirect('/workflow/build_from_current_history')">
                        <Icon fixed-width icon="file-export" class="mr-1" />
                        <span v-localize>Extract Workflow</span>
                    </GDropdownItem>

                    <GDropdownItem
                        :disabled="isAnonymous"
                        class="dropdown-item"
                        :title="userTitle('Display Workflow Invocations')"
                        @click="$router.push(`/histories/${history.id}/invocations`)">
                        <Icon fixed-width icon="sitemap" class="fa-rotate-270 mr-1" />
                        <span v-localize>Show Invocations</span>
                    </GDropdownItem>

                    <GDropdownDivider />

                    <GDropdownItem
                        :disabled="isAnonymous"
                        class="dropdown-item"
                        :title="userTitle('Share or Publish this History')"
                        data-description="share or publish"
                        @click="$router.push(`/histories/sharing?id=${history.id}`)">
                        <Icon fixed-width icon="share-alt" class="mr-1" />
                        <span v-localize>Share or Publish</span>
                    </GDropdownItem>

                    <GDropdownItem
                        :disabled="isAnonymous"
                        class="dropdown-item"
                        :title="userTitle('Set who can View or Edit this History')"
                        @click="$router.push(`/histories/permissions?id=${history.id}`)">
                        <Icon fixed-width icon="user-lock" class="mr-1" />
                        <span v-localize>Set Permissions</span>
                    </GDropdownItem>

                    <GDropdownItem
                        v-b-modal:history-privacy-modal
                        class="dropdown-item"
                        :disabled="isAnonymous"
                        :title="userTitle('Make this History Private')">
                        <Icon fixed-width icon="lock" class="mr-1" />
                        <span v-localize>Make Private</span>
                    </GDropdownItem>
                </GDropdown>
            </GButtonGroup>
        </nav>

        <SelectorModal
            v-show="showSwitchModal"
            id="selector-history-modal"
            :histories="histories"
            :additional-options="['center', 'multi']"
            :show-modal.sync="showSwitchModal"
            @selectHistory="setCurrentHistory($event.id)" />

        <CopyModal id="copy-current-history-modal" :history="history" />

        <GModal id="history-privacy-modal" title="Make History Private" title-tag="h2" @ok="secureHistory(history)">
            <p v-localize>
                This will make all the data in this history private (excluding library datasets), and will set
                permissions such that all new data is created as private. Any datasets within that are currently shared
                will need to be re-shared or published. Are you sure you want to do this?
            </p>
        </GModal>

        <GModal id="delete-history-modal" title="Delete History?" title-tag="h2" @ok="deleteHistory(history.id)">
            <p v-localize>Really delete the current history?</p>
        </GModal>

        <GModal
            id="purge-history-modal"
            title="Permanently Delete History?"
            title-tag="h2"
            @ok="deleteHistory(history.id, true)">
            <p v-localize>Really delete the current history permanently? This cannot be undone.</p>
        </GModal>
    </div>
</template>

<script>
import CopyModal from "components/History/Modals/CopyModal";
import SelectorModal from "components/History/Modals/SelectorModal";
import { legacyNavigationMixin } from "components/plugins/legacyNavigation";
import { mapActions, mapState } from "pinia";

import {
    GButton,
    GButtonGroup,
    GDropdown,
    GDropdownDivider,
    GDropdownItem,
    GDropdownText,
    GModal,
    GSpinner,
} from "@/component-library";
import { useHistoryStore } from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";

export default {
    components: {
        CopyModal,
        GButton,
        GButtonGroup,
        GDropdown,
        GDropdownDivider,
        GDropdownItem,
        GDropdownText,
        GModal,
        GSpinner,
        SelectorModal,
    },
    mixins: [legacyNavigationMixin],
    props: {
        histories: { type: Array, required: true },
        history: { type: Object, required: true },
        title: { type: String, default: "Histories" },
        historiesLoading: { type: Boolean, default: false },
    },
    data() {
        return {
            showSwitchModal: false,
        };
    },
    computed: {
        ...mapState(useUserStore, ["isAnonymous"]),
        ...mapState(useHistoryStore, ["totalHistoryCount"]),
    },
    methods: {
        ...mapActions(useHistoryStore, ["createNewHistory", "deleteHistory", "secureHistory", "setCurrentHistory"]),
        userTitle(title) {
            if (this.isAnonymous) {
                return this.l("Log in to") + " " + this.l(title);
            } else {
                return this.l(title);
            }
        },
    },
};
</script>

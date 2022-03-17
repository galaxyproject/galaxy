<template>
    <div>
        <b-dropdown
            size="sm"
            variant="link"
            text="Histories"
            toggle-class="text-decoration-none"
            data-description="history menu">
            <template v-slot:button-content>
                <Icon fixed-width icon="cog" />
                <span class="sr-only">Operations on the current history</span>
            </template>

            <b-dropdown-item v-b-modal:copy-history-modal>
                <Icon fixed-width icon="copy" class="mr-1" />
                <span v-localize>Copy this History</span>
            </b-dropdown-item>

            <b-dropdown-item v-b-modal:delete-history-modal>
                <Icon fixed-width icon="trash" class="mr-1" />
                <span v-localize>Delete this History</span>
            </b-dropdown-item>

            <b-dropdown-item v-b-modal:purge-history-modal>
                <Icon fixed-width icon="burn" class="mr-1" />
                <span v-localize>Purge this History</span>
            </b-dropdown-item>

            <b-dropdown-divider></b-dropdown-divider>

            <b-dropdown-item @click="iframeRedirect('/history/resume_paused_jobs?current=True')">
                <Icon fixed-width icon="play" class="mr-1" />
                <span v-localize>Resume Paused Jobs</span>
            </b-dropdown-item>

            <b-dropdown-item @click="iframeRedirect('/workflow/build_from_current_history')">
                <Icon fixed-width icon="file-export" class="mr-1" />
                <span v-localize>Extract Workflow</span>
            </b-dropdown-item>

            <b-dropdown-item @click="backboneRoute('/histories/show_structure')" data-description="show structure">
                <Icon fixed-width icon="code-branch" class="mr-1" />
                <span v-localize>Show Structure</span>
            </b-dropdown-item>

            <b-dropdown-divider></b-dropdown-divider>

            <b-dropdown-item @click="backboneRoute('/histories/sharing', { id: history.id })">
                <Icon fixed-width icon="share-alt" class="mr-1" />
                <span v-localize>Share or Publish</span>
            </b-dropdown-item>

            <b-dropdown-item @click="backboneRoute('/histories/permissions', { id: history.id })">
                <Icon fixed-width icon="user-lock" class="mr-1" />
                <span v-localize>Set Permissions</span>
            </b-dropdown-item>

            <b-dropdown-item v-b-modal:history-privacy-modal>
                <Icon fixed-width icon="lock" class="mr-1" />
                <span v-localize>Make Private</span>
            </b-dropdown-item>

            <b-dropdown-divider></b-dropdown-divider>

            <b-dropdown-item @click="backboneRoute('/histories/citations', { id: history.id })">
                <Icon fixed-width icon="stream" class="mr-1" />
                <span v-localize>Export Tool Citations</span>
            </b-dropdown-item>

            <b-dropdown-item @click="backboneRoute(history.exportLink)" data-description="export to file">
                <Icon fixed-width icon="file-archive" class="mr-1" />
                <span v-localize>Export History to File</span>
            </b-dropdown-item>
        </b-dropdown>

        <!-- #region modals -->

        <CopyHistoryModal id="copy-history-modal" :history="history" />

        <b-modal
            id="history-privacy-modal"
            title="Make History Private"
            title-tag="h2"
            @ok="$emit('secureHistory', history)">
            <p v-localize>
                This will make all the data in this history private (excluding library datasets), and will set
                permissions such that all new data is created as private. Any datasets within that are currently shared
                will need to be re-shared or published. Are you sure you want to do this?
            </p>
        </b-modal>

        <b-modal id="delete-history-modal" title="Delete History?" title-tag="h2" @ok="$emit('deleteHistory', history)">
            <p v-localize>Really delete the current history?</p>
        </b-modal>

        <b-modal
            id="purge-history-modal"
            title="Permanently Delete History?"
            title-tag="h2"
            @ok="$emit('purgeHistory', history)">
            <p v-localize>Really delete the current history permanently? This cannot be undone.</p>
        </b-modal>

        <!-- #endregion -->
    </div>
</template>

<script>
import { History } from "./model";
import CopyHistoryModal from "./CopyModal";
import { legacyNavigationMixin } from "components/plugins/legacyNavigation";

export default {
    mixins: [legacyNavigationMixin],
    components: {
        CopyHistoryModal,
    },
    props: {
        history: { type: History, required: true },
    },
};
</script>

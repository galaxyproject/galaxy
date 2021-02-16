<template>
    <header>
        <div class="d-flex justify-content-between align-items-center">
            <h6 class="text-nowrap text-truncate mr-auto">
                <span class="size">{{ history.niceSize | localize }}</span>
            </h6>

            <PriorityMenu style="max-width: 50%;" :starting-height="28">
                <PriorityMenuItem
                    key="edit-history-tags"
                    title="Edit History Tags"
                    icon="fas fa-tags"
                    :pressed="showTags"
                    @click="showTags = !showTags"
                />
                <PriorityMenuItem
                    key="edit-history-annotation"
                    title="Edit Annotation"
                    icon="fas fa-comment"
                    :pressed="showAnnotation"
                    @click="showAnnotation = !showAnnotation"
                />
                <PriorityMenuItem
                    key="copy-history"
                    title="Copy History"
                    icon="fas fa-copy"
                    @click="showCopyModal = !showCopyModal"
                />
                <PriorityMenuItem
                    key="share"
                    title="Share or Publish"
                    icon="fas fa-handshake"
                    @click="backboneRoute('/histories/sharing', { id: history.id })"
                />
                <PriorityMenuItem
                    key="delete-this-history"
                    title="Delete this History"
                    icon="fas fa-trash"
                    @click="showDeleteModal = !showDeleteModal"
                />
                <PriorityMenuItem
                    key="purge-this-history"
                    title="Purge this History"
                    icon="fas fa-burn"
                    @click="showPurgeModal = !showPurgeModal"
                />
                <PriorityMenuItem
                    key="structure"
                    title="Show Structure"
                    icon="fas fa-code-branch"
                    @click="backboneRoute('/histories/show_structure')"
                />
                <PriorityMenuItem
                    key="extract-workflow"
                    title="Extract Workflow"
                    icon="fas fa-file-export"
                    @click="iframeRedirect('/workflow/build_from_current_history')"
                />
                <PriorityMenuItem
                    key="set-permissions"
                    title="Set Permissions"
                    icon="fas fa-user-lock"
                    @click="backboneRoute('/histories/permissions', { id: history.id })"
                />
                <PriorityMenuItem
                    key="make-private"
                    title="Make Private"
                    icon="fas fa-lock"
                    @click="showPrivacyModal = !showPrivacyModal"
                />
                <PriorityMenuItem
                    key="resume-paused-jobs"
                    title="Resume Paused Jobs"
                    icon="fas fa-play"
                    @click="iframeRedirect('/history/resume_paused_jobs?current=True')"
                />
                <PriorityMenuItem
                    key="export-citations"
                    title="Export Tool Citations"
                    icon="fas fa-stream"
                    @click="backboneRoute('/histories/citations', { id: history.id })"
                />
                <PriorityMenuItem
                    key="export-history-to-file"
                    title="Export History to File"
                    icon="fas fa-file-archive"
                    @click="iframeRedirect('/history/export_archive?preview=True')"
                />
            </PriorityMenu>
        </div>

        <!-- click to edit the name of the history -->
        <ClickToEdit
            class="history-title mt-2"
            tag-name="h3"
            v-model="historyName"
            :tooltip-title="'Rename history...' | localize"
            tooltip-placement="top"
        />

        <transition name="shutterfade">
            <Annotation v-if="showAnnotation" class="history-annotation mt-2" v-model="annotation" />
        </transition>

        <transition name="shutterfade">
            <HistoryTags v-if="showTags" class="mt-2" :history="history" />
        </transition>

        <!-- #region modals -->

        <CopyHistoryModal v-model="showCopyModal" :history="history" />

        <b-modal v-model="showPrivacyModal" title="Make History Private" title-tag="h2" @ok="makePrivate">
            <p v-localize>
                This will make all the data in this history private (excluding library datasets), and will set
                permissions such that all new data is created as private. Any datasets within that are currently shared
                will need to be re-shared or published. Are you sure you want to do this?
            </p>
        </b-modal>

        <b-modal v-model="showDeleteModal" title="Delete History?" title-tag="h2" @ok="deleteHistory">
            <p v-localize>Really delete the current history?</p>
        </b-modal>

        <b-modal v-model="showPurgeModal" title="Permanently Delete History?" title-tag="h2" @ok="purgeHistory">
            <p v-localize>Really delete the current history permanently? This cannot be undone.</p>
        </b-modal>

        <!-- #endregion -->
    </header>
</template>

<script>
import { History } from "./model";
import { PriorityMenuItem, PriorityMenu } from "components/PriorityMenu";
import { legacyNavigationMixin } from "components/plugins/legacyNavigation";
import ClickToEdit from "components/ClickToEdit";
import Annotation from "components/Annotation";
import HistoryTags from "./HistoryTags";
import CopyHistoryModal from "./CopyModal";

export default {
    mixins: [legacyNavigationMixin],
    components: {
        PriorityMenu,
        PriorityMenuItem,
        HistoryTags,
        Annotation,
        ClickToEdit,
        CopyHistoryModal,
    },
    props: {
        history: { type: History, required: true },
    },
    data() {
        return {
            showTags: false,
            showAnnotation: false,
            showCopyModal: false,
            showPrivacyModal: false,
            showDeleteModal: false,
            showPurgeModal: false,
        };
    },
    computed: {
        annotation: {
            get() {
                return this.history.annotation || "";
            },
            set(annotation) {
                if (annotation.length && annotation !== this.history.annotation) {
                    this.updateFields({ annotation });
                }
            },
        },

        historyName: {
            get() {
                return this.history?.name || "";
            },
            set(name) {
                if (name.length && name !== this.history.name) {
                    this.updateFields({ name });
                }
            },
        },
    },
    methods: {
        async updateFields(fields = {}) {
            this.$emit("updateHistory", { id: this.history.id, ...fields });
        },
        async deleteHistory(evt) {
            this.$emit("deleteHistory", this.history);
            evt.vueTarget.hide();
        },
        async purgeHistory(evt) {
            this.$emit("purgeHistory", this.history);
            evt.vueTarget.hide();
        },
        async makePrivate(evt) {
            this.$emit("secureHistory", this.history);
            evt.vueTarget.hide();
        },
    },
};
</script>

<style lang="scss">
@import "scss/transitions.scss";
</style>

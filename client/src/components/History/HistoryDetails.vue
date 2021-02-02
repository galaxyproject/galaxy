<template>
    <section>
        <header class="d-flex justify-content-between align-items-center">
            <h6 class="text-nowrap text-truncate mr-auto">
                <span class="size">{{ history.niceSize | localize }}</span>
            </h6>

            <PriorityMenu style="max-width: 50%" :starting-height="27">
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
                    @click="showCopyModal = true"
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
                    @click="$bvModal.show('delete-history-modal')"
                />

                <PriorityMenuItem
                    key="purge-this-history"
                    title="Purge this History"
                    icon="fas fa-burn"
                    @click="$bvModal.show('purge-history-modal')"
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
                    @click="$bvModal.show('make-private-modal')"
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
                    @click="backboneRoute(`/histories/${history.id}/export`)"
                />
            </PriorityMenu>

            <CopyModal v-model="showCopyModal" :history="history" />

            <b-modal id="make-private-modal" title="Make History Private" title-tag="h2" @ok="makePrivate">
                <p v-localize>
                    This will make all the data in this history private (excluding library datasets), and will set
                    permissions such that all new data is created as private. Any datasets within that are currently
                    shared will need to be re-shared or published. Are you sure you want to do this?
                </p>
            </b-modal>

            <b-modal id="delete-history-modal" title="Delete History?" title-tag="h2" @ok="deleteHistoryClick">
                <p v-localize>Really delete the current history?</p>
            </b-modal>

            <b-modal
                id="purge-history-modal"
                title="Permanently Delete History?"
                title-tag="h2"
                @ok="purgeHistoryClick"
            >
                <p v-localize>Really delete the current history permanently? This cannot be undone.</p>
            </b-modal>
        </header>

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
    </section>
</template>

<script>
import { mapActions } from "vuex";

import { History } from "./model";
import { deleteHistoryById, updateHistoryFields, secureHistory } from "./model/queries";

import ClickToEdit from "components/ClickToEdit";
import Annotation from "components/Annotation";
import { PriorityMenuItem, PriorityMenu } from "components/PriorityMenu";
import HistoryTags from "./HistoryTags";
import CopyModal from "./CopyModal";
import { legacyNavigationMixin } from "components/plugins";

export default {
    mixins: [legacyNavigationMixin],
    components: {
        HistoryTags,
        CopyModal,
        Annotation,
        ClickToEdit,
        PriorityMenu,
        PriorityMenuItem,
    },
    props: {
        history: { type: History, required: true },
    },
    data() {
        return {
            showTags: false,
            showAnnotation: false,
            showCopyModal: false,
            editAnnotation: false,
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
                return this.history.name;
            },
            set(name) {
                if (name.length && name !== this.history.name) {
                    this.updateFields({ name });
                }
            },
        },
    },
    methods: {
        ...mapActions("betaHistory", ["storeHistory"]),

        async updateFields(fields = {}) {
            const updatedHistory = await updateHistoryFields(this.history, fields);
            await this.storeHistory(updatedHistory);
        },

        async deleteHistoryClick(evt) {
            const updatedHistory = await deleteHistoryById(this.history.id);
            // console.log("deleteHistoryClick", updatedHistory);
            await this.storeHistory(updatedHistory);
            evt.vueTarget.hide();
        },

        async purgeHistoryClick(evt) {
            const updatedHistory = await deleteHistoryById(this.history.id, true);
            // console.log("purgeHistoryClick", updatedHistory);
            await this.storeHistory(updatedHistory);
            evt.vueTarget.hide();
        },

        async makePrivate(evt) {
            const updatedHistory = await secureHistory(this.history.id);
            await this.storeHistory(updatedHistory);
            evt.vueTarget.hide();
        },
    },
};
</script>

<style lang="scss">
@import "scss/transitions.scss";
</style>

<!--
History object editor. Change name, edit tags, description.
Emit new History model object when done via .sync syntax
-->

<template>
    <section class="history-details d-flex">
        <div class="flex-grow-1 overflow-hidden">
            <h3 data-description="history name display">{{ historyName || "(History Name)" }}</h3>
            <h5 class="history-size">{{ history.size | niceFileSize }}</h5>

            <!-- display title, annotation, tags -->
            <div v-if="!editing">
                <p v-if="annotation" class="mt-1">{{ annotation }}</p>
                <HistoryTags class="mt-2" :history="history" :disabled="true" />
            </div>

            <!-- edit form, change title, annotation, or tags -->
            <div v-else class="mt-3">
                <b-textarea
                    class="mb-2"
                    v-model="historyName"
                    placeholder="History Name"
                    trim
                    max-rows="4"
                    data-description="history name input"
                ></b-textarea>

                <b-textarea
                    class="mb-2"
                    v-model="annotation"
                    placeholder="Annotation (optional)"
                    trim
                    max-rows="4"
                    data-description="history annotation input"
                ></b-textarea>

                <HistoryTags class="mt-3" :history="history" />
            </div>
        </div>

        <EditorMenu
            class="ml-3 flex-grow-0 d-flex flex-column"
            v-if="writable"
            model-name="History"
            :editing.sync="editing"
            :writable="writable"
            :valid="valid"
            :dirty="dirty"
            @save="save"
            @revert="revert"
        />
    </section>
</template>

<script>
import prettyBytes from "pretty-bytes";
import { History } from "./model";
import HistoryTags from "./HistoryTags";
import EditorMenu from "./EditorMenu";

export default {
    components: {
        HistoryTags,
        EditorMenu,
    },
    filters: {
        niceFileSize(rawSize = 0) {
            return prettyBytes(rawSize);
        },
    },
    props: {
        history: { type: History, required: true },
        writable: { type: Boolean, required: false, default: true },
    },
    data() {
        return {
            editing: false,
            tempHistory: this.history.clone(),
        };
    },
    computed: {
        historyId() {
            return this.history.id;
        },
        isEditing() {
            return this.writable && this.editing;
        },
        valid() {
            return this.tempHistory.name.length > 0;
        },
        dirty() {
            return !this.tempHistory.equals(this.history);
        },
        annotation: {
            get() {
                return this.tempHistory.annotation;
            },
            set(annotation) {
                this.patchTempHistory({ annotation });
            },
        },
        historyName: {
            get() {
                return this.tempHistory.name;
            },
            set(name) {
                this.patchTempHistory({ name });
            },
        },
        tags: {
            get() {
                return this.tempHistory.tags || [];
            },
            set(newTags) {
                this.patchTempHistory({ tags: newTags });
            },
        },
    },
    watch: {
        historyId(newId, oldId) {
            if (newId != oldId) {
                this.reset();
            }
        },
    },
    methods: {
        reset() {
            this.tempHistory = this.history.clone();
        },
        patchTempHistory(props = {}) {
            this.tempHistory = this.tempHistory.patch(props);
        },
        save() {
            if (this.valid) {
                this.$emit("update:history", this.tempHistory);
                this.editing = false;
            }
        },
        revert() {
            if (this.dirty) {
                this.reset();
            }
        },
    },
};
</script>

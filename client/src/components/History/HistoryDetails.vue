<!--
History object editor. Change name, edit tags, description.
Emit new History model object when done via .sync syntax
-->

<template>
    <section class="history-details d-flex" data-description="edit details">
        <div class="flex-grow-1 overflow-hidden">
            <h3 data-description="history name display">{{ historyName || "(History Name)" }}</h3>
            <h5 class="history-size">
                <span v-if="history.size">{{ history.size | niceFileSize }}</span>
                <span v-else v-localize>(empty)</span>
            </h5>

            <!-- display title, annotation, tags -->
            <div v-if="!editing">
                <p data-description="history annotation" v-if="annotation" class="mt-1">{{ annotation }}</p>
                <StatelessTags class="mt-2 tags" :value="tags" :disabled="true" />
            </div>

            <!-- edit form, change title, annotation, or tags -->
            <div v-else class="mt-3" @keydown.esc="revertAndCancel" data-description="edit form">
                <b-textarea
                    class="mb-2"
                    v-model="historyName"
                    placeholder="History Name"
                    trim
                    max-rows="4"
                    data-description="name input"></b-textarea>

                <b-textarea
                    class="mb-2"
                    v-model="annotation"
                    placeholder="Annotation (optional)"
                    trim
                    max-rows="4"
                    data-description="annotation input"></b-textarea>

                <StatelessTags class="mt-3 tags" v-model="tags" />
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
            @revert="revert" />
    </section>
</template>

<script>
import prettyBytes from "pretty-bytes";
import { History } from "./model";
import EditorMenu from "./EditorMenu";
import { StatelessTags } from "components/Tags";

export default {
    components: {
        EditorMenu,
        StatelessTags,
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
        revertAndCancel() {
            this.revert();
            this.editing = false;
        },
    },
};
</script>

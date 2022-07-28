<template>
    <section class="m-3 details" data-description="edit details">
        <b-button
            v-if="!currentUser.isAnonymous && writeable"
            class="edit-button ml-1 float-right"
            data-description="editor toggle"
            size="sm"
            variant="link"
            :title="'Edit' | l"
            :pressed="editing"
            @click="onToggle">
            <Icon icon="pen" />
        </b-button>
        <slot name="name" />

        <!-- display annotation, tags -->
        <div v-if="!editing">
            <div v-if="annotation" v-short="annotation" class="mt-2" data-description="annotation value" />
            <StatelessTags v-if="tags" class="tags mt-2" :value="tags" :disabled="true" />
        </div>

        <!-- edit form, change title, annotation, or tags -->
        <div v-else class="mt-3" data-description="edit form">
            <b-input
                ref="name"
                v-model="localProps.name"
                class="mb-2"
                placeholder="Name"
                trim
                max-rows="4"
                data-description="name input"
                @keyup.enter="onSave"
                @keyup.esc="onToggle" />
            <b-textarea
                v-if="showAnnotation"
                v-model="localProps.annotation"
                class="mb-2"
                placeholder="Annotation (optional)"
                trim
                max-rows="4"
                data-description="annotation input"
                @keyup.esc="onToggle" />
            <StatelessTags v-if="localProps.tags" v-model="localProps.tags" class="mb-3 tags" />
            <b-button
                class="save-button mb-1"
                data-description="editor save button"
                size="sm"
                variant="primary"
                :disabled="!localProps.name"
                @click="onSave">
                <Icon icon="save" />
                <span v-localize>Save</span>
            </b-button>
            <b-button
                class="cancel-button mb-1"
                data-description="editor cancel button"
                size="sm"
                icon="undo"
                @click="onToggle">
                <Icon icon="undo" />
                <span v-localize>Cancel</span>
            </b-button>
        </div>
    </section>
</template>

<script>
import { mapGetters } from "vuex";
import short from "components/directives/v-short";
import { StatelessTags } from "components/Tags";

export default {
    components: {
        StatelessTags,
    },
    directives: {
        short,
    },
    props: {
        name: { type: String, default: null },
        annotation: { type: String, default: null },
        showAnnotation: { type: Boolean, default: true },
        tags: { type: Array, default: null },
        writeable: { type: Boolean, default: true },
    },
    data() {
        return {
            editing: false,
            localProps: {},
        };
    },
    computed: {
        ...mapGetters("user", ["currentUser"]),
    },
    methods: {
        onSave() {
            this.editing = false;
            this.$emit("save", Object.assign({}, this.localProps));
        },
        onToggle() {
            this.editing = !this.editing;
            this.localProps = {
                name: this.name,
                annotation: this.annotation,
                tags: this.tags,
            };
            // After dom update, focus on input
            this.$nextTick(() => {
                if (this.$refs.name) {
                    this.$refs.name.focus();
                }
            });
        },
    },
};
</script>

<template>
    <section data-description="edit details">
        <b-button
            v-if="writeable"
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
            <div v-if="annotation" class="mt-2" data-description="annotation value">{{ annotation }}</div>
            <StatelessTags v-if="tags" class="tags mt-2" :value="tags" :disabled="true" />
        </div>

        <!-- edit form, change title, annotation, or tags -->
        <div v-else class="mt-3" data-description="edit form">
            <b-textarea
                class="mb-2"
                v-model="localProps.name"
                placeholder="Name"
                trim
                max-rows="4"
                data-description="name input"
                @keyup.esc="onToggle" />
            <b-textarea
                v-if="showAnnotation"
                class="mb-2"
                v-model="localProps.annotation"
                placeholder="Annotation (optional)"
                trim
                max-rows="4"
                data-description="annotation input"
                @keyup.esc="onToggle" />
            <StatelessTags v-if="localProps.tags" class="mb-3 tags" v-model="localProps.tags" />
        </div>
        <nav class="edit-controls">
            <template v-if="editing">
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
            </template>
        </nav>
    </section>
</template>

<script>
import { StatelessTags } from "components/Tags";
export default {
    components: {
        StatelessTags,
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
    watch: {
        name() {
            this.localProps.name = this.name;
        },
        annotation() {
            this.localProps.annotation = this.annotation;
        },
        tags() {
            this.localProps.tags = this.tags;
        },
    },
    created() {
        this.onReset();
    },
    methods: {
        onReset() {
            this.localProps = {
                name: this.name,
                annotation: this.annotation,
                tags: this.tags,
            };
        },
        onSave() {
            this.editing = false;
            this.$emit("save", Object.assign({}, this.localProps));
        },
        onToggle() {
            this.editing = !this.editing;
            this.onReset();
        },
    },
};
</script>

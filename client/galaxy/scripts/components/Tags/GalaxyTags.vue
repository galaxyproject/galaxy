<template>
    <div :class="tagContainerClasses">
        <a href="#" class="toggle-link" 
            v-if="linkVisible"
            @click.prevent="toggleTagDisplay">
            {{ linkText | localize }}
        </a>
        <vue-tags-input class="tag-area" 
            v-if="tagsVisible" 
            v-model="tagText"
            :tags="tagModels"
            :autocomplete-items="autocompleteTags"
            :disabled="disabled"
            :placeholder="'Add Tags' | localize"
            :add-on-key="[13, ' ']"
            @before-adding-tag="beforeAddingTag"
            @before-deleting-tag="beforeDeletingTag"
            @tags-changed="tagsChanged">
            <div class="tag-name" slot="tag-center" slot-scope="tagProps" 
                @click="$emit('tag-click', tagProps.tag)">
                {{ tagProps.tag.text }}
            </div>
        </vue-tags-input>
    </div>
</template>

<script>

import VueTagsInput from "@johmun/vue-tags-input";
import { createTag } from "./model";

export default {
    components: {
        VueTagsInput
    },
    props: {
        value: { type: Array, required: false, default: () => [] },
        autocompleteItems: { type: Array, required: false, default: () => ([]) },
        maxVisibleTags: { type: Number, required: false, default: 5 },
        useToggleLink: { type: Boolean, required: false, default: true },
        disabled: { type: Boolean, required: false, default: false }
    },
    data() {
        
        // initialize toggle value
        let isClosed = this.useToggleLink && (this.value.length > this.maxVisibleTags);
        
        return { 
            // text of the new tag, when editable
            tagText: "",
            // if list is too long and we're using the toggle, then hide the tags
            tagToggle: !isClosed
        }
    },
    computed: {
        tagContainerClasses() {
            return {
                "galaxy-tags": true,
                "disabled": this.disabled
            }
        },
        tagModels() {
            return this.value.map(createTag);
        },
        autocompleteTags() {
            return this.autocompleteItems.map(createTag);
        },
        linkText() {
            return `${this.tagModels.length} Tags`;
        },
        linkVisible() {
            return this.useToggleLink && (this.tagModels.length > this.maxVisibleTags);
        },
        tagsVisible() {
            return this.useToggleLink ? this.tagToggle : true;
        }
    },
    watch: {
        tagText(newValue) {
            this.$emit("tag-input-changed", newValue);
        }
    },
    methods: {
        tagsChanged(newTags) {
            this.$emit('input', this.pluckLabels(newTags));
        },
        pluckLabels(newTags) {
            return newTags.map(t => createTag(t).toString());
        },
        toggleTagDisplay() {
            this.tagToggle = !this.tagToggle;
            this.$emit("show", this.tagToggle);
        },
        beforeAddingTag($event) {
            if (!this.emitHookEvent("before-adding-tag", $event)) {
                let { tag, addTag } = $event;
                addTag(tag);
            }
        },
        beforeDeletingTag($event) {
            if (!this.emitHookEvent("before-deleting-tag", $event)) {
                let { tag, deleteTag } = $event;
                deleteTag(tag);
            }
        },
        emitHookEvent(eventName, $event) {
            if (this.hasHandler(eventName)) {
                this.$emit(eventName, $event);
                return true;
            }
            return false;
        },
        hasHandler(eventName) {
            return Object.keys(this.$listeners).includes(eventName);
        }
    }
}

</script>

<style lang="scss" src="./tagStyles.scss"></style>

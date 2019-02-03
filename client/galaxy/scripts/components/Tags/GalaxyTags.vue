<!--
Configurable tag component. Needed to do some minor event/property remapping
to make the 3rd party component suit the interface I wanted to expose. This 
component is used like a glorified form input with v-model. Set v-model
to the array of selected tags.

Props: 
    "value":
        Standard vue property that is assigned when v-model="tags" is set.
        No need to set it directly, just use v-model="tags"
    autoCompleteItems: 
        An array of autocomplete items for the current tag text. You can capture
        changes to the tag being entered in the tag-input-changed event and reset
        this property as required

Events:
    "input" (standard v-model update event, Not used directly):
        Emits when list of tags change
    before-adding-tag({ tag, addTag })
        Hook allowing user the chance to do an operation before
        commiting a tag to the list
    before-deleting-tag({ tag, deleteTag })
        Hook allowing consumer to do somehting before removing
        a tag from the displayed list.
    tag-click:
        When the central name display of the tag is clicked, can
        assign a handler from the consuming environment
    tag-input-changed:
        As user is typing a new tag, the text gets emitted here.

Usage:

    <galaxy-tags 
        v-model="tags" 
        :autocomplete-items="autocompleteItems"
        @tag-click="tagClick"
        @tag-input-changed="tagTextChanged"
        @before-adding-tag="beforeAddingTag"
        @before-deleting-tag="beforeDeletingTag"
    />

    ...

    methods: {

        // tag is only added when addTag(tag) is called
        beforeAddingTag({ tag, addTag }) {
            saveTagToServer().then(() => addTag(tag));
        },

        // tag is deleted when deleteTag(tag) is called
        beforeDeletingTag({ tag, deleteTag }) {
            deleteTagFromServer().then(() => deleteTag(tag));
        },

        // do a database lookup to generate viable options and
        // set on the property that's passed to the component to
        // do a little autocomplete dropdown
        tagTextChanged(txt) {
            generateAutocompleteOptions(txt).then((newOptions) => {
                this.autocompleteItems = newOptions;
            })
        },

        // any appropriate click handler (update search, etc.)
        tagClick(tag) {
            // do something with the tag data
        }
    }

-->

<template>
    <div>
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

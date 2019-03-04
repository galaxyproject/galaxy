<template>
    <div :class="tagContainerClasses">
        <a href="#" class="toggle-link" v-if="linkVisible" @click.prevent="toggleTagDisplay">
            {{ linkText | localize }}
        </a>
        <vue-tags-input
            class="tag-area"
            v-if="tagsVisible"
            v-model="tagText"
            :tags="tagModels"
            :autocomplete-items="autocompleteTags"
            :disabled="disabled"
            :placeholder="'Add Tags' | localize"
            :add-on-key="[13, ' ']"
            @before-adding-tag="beforeAddingTag"
            @before-deleting-tag="beforeDeletingTag"
            @tags-changed="tagsChanged"
        >
            <div class="tag-name" slot="tag-center" slot-scope="tagProps" @click="$emit('tag-click', tagProps.tag)">
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
        autocompleteItems: { type: Array, required: false, default: () => [] },
        maxVisibleTags: { type: Number, required: false, default: 5 },
        useToggleLink: { type: Boolean, required: false, default: true },
        disabled: { type: Boolean, required: false, default: false }
    },
    data() {
        // initialize toggle value
        let isClosed = this.useToggleLink && this.value.length > this.maxVisibleTags;

        return {
            // text of the new tag, when editable
            tagText: "",
            // if list is too long and we're using the toggle, then hide the tags
            tagToggle: !isClosed
        };
    },
    computed: {
        tagContainerClasses() {
            return {
                "galaxy-tags": true,
                disabled: this.disabled
            };
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
            return this.useToggleLink && this.tagModels.length > this.maxVisibleTags;
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
            this.$emit("input", this.pluckLabels(newTags));
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
};
</script>

<style lang="scss">
@import "theme/blue";
@import "scss/mixins";

// Puts a little graphic in place of the text-input
// when the input is not in focus
@mixin newTagHoverButton() {
    .vue-tags-input .ti-tags .ti-new-tag-input-wrapper {
        input {
            background-color: transparent;
        }
        input:not(:focus) {
            background: url("/static/images/fugue/tag--plus.png");
            background-repeat: no-repeat;
            color: transparent;
            &::placeholder {
                color: transparent;
            }
        }
    }
}

// hides tag container edges
@mixin hideEditorBorders() {
    .vue-tags-input {
        // need to add yet another class to beat the scoping
        &.tag-area {
            background-color: transparent;
        }
        .ti-input {
            border: none;
        }
    }
}

// general style butchering
@mixin matchBootstrapStyling() {
    .vue-tags-input {
        @include fill();
        .ti-input {
            padding: 0;
        }
        .ti-tag {
            border-radius: 4px;
            font-size: 0.8rem;
            font-weight: 400;
        }
    }
}

// Version of the tags that only allow clicking
// existing tags instead of the full editing UI
@mixin forDisplayOnly() {
    .vue-tags-input {
        .ti-actions,
        .ti-new-tag-input-wrapper {
            display: none;
        }
    }
}

.galaxy-tags {
    // adds in a graphic in place of the text input
    @include newTagHoverButton();

    // match bootstrap tag styles/colors
    @include matchBootstrapStyling();

    // removes input borders (not sure if this happens everywhere)
    @include hideEditorBorders();

    // display-only tags
    &.disabled {
        @include forDisplayOnly();
    }
}
</style>

<!-- This is intended to be a stateless UI-only component. All data storage and
retrieval as well as and specific event handling should be managed from an
upstream component or environment that is accessed through props and events -->

<template>
    <div class="tags-display" :class="tagContainerClasses">
        <a
            v-if="linkVisible"
            href="javascript:void(0)"
            role="button"
            class="toggle-link"
            @click.prevent="toggleTagDisplay">
            {{ linkText }}
        </a>
        <vue-tags-input
            v-if="tagsVisible"
            v-model="tagText"
            class="tags-input tag-area"
            :tags="tagModels"
            :autocomplete-items="autocompleteTags"
            :disabled="disabled"
            placeholder="Add Tags"
            :add-on-key="triggerKeys"
            :validation="validation"
            @before-adding-tag="beforeAddingTag"
            @before-deleting-tag="beforeDeletingTag"
            @tags-changed="tagsChanged">
            <template v-slot:tag-center="t">
                <div class="tag-name" @click="$emit('tag-click', t.tag)">{{ t.tag.label }}</div>
            </template>
        </vue-tags-input>
    </div>
</template>

<script>
import VueTagsInput from "@johmun/vue-tags-input";
import { createTag, VALID_TAG_RE } from "./model";

export default {
    components: {
        VueTagsInput,
    },
    props: {
        value: { type: Array, required: false, default: () => [] },
        autocompleteItems: { type: Array, required: false, default: () => [] },
        maxVisibleTags: { type: Number, required: false, default: 5 },
        useToggleLink: { type: Boolean, required: false, default: true },
        disabled: { type: Boolean, required: false, default: false },
    },
    data() {
        // initialize toggle value
        const isClosed = this.useToggleLink && this.value.length > this.maxVisibleTags;

        return {
            tagText: "",
            tagToggle: !isClosed,
            triggerKeys: [13, " "],
            validation: [
                {
                    classes: "error",
                    rule: VALID_TAG_RE,
                },
            ],
        };
    },
    computed: {
        tagContainerClasses() {
            return {
                disabled: this.disabled,
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
        },
    },
    watch: {
        tagText(newValue) {
            this.$emit("tag-input-changed", newValue);
        },
    },
    methods: {
        tagsChanged(newTags) {
            this.$emit("input", this.pluckLabels(newTags));
        },
        pluckLabels(newTags) {
            return newTags.map((t) => createTag(t).toString());
        },
        toggleTagDisplay() {
            this.tagToggle = !this.tagToggle;
            this.$emit("show", this.tagToggle);
        },
        beforeAddingTag($event) {
            if (!this.emitHookEvent("before-adding-tag", $event)) {
                const { tag, addTag } = $event;
                addTag(tag);
            }
        },
        beforeDeletingTag($event) {
            if (!this.emitHookEvent("before-deleting-tag", $event)) {
                const { tag, deleteTag } = $event;
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
        },
    },
};
</script>

<style lang="scss">
// Most styling of the tags should happen in here.

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
            background: url("../../assets/images/tags-solid.svg");
            background-repeat: no-repeat;
            color: transparent;
            &::placeholder {
                color: transparent;
            }
        }
    }
}

// general style butchering
@mixin matchBootstrapStyling() {
    // TODO: actually match the bootstrap button classes in
    // here either by importing mixins or just using colors
    // from the boostrap .scss files
    .vue-tags-input {
        @include fill();
        .ti-input {
            padding: 0;
            border: none;

            .ti-new-tag-input {
                &.error:focus {
                    //TODO: These relative URLs are unfortunate.
                    background: url("../../../node_modules/@fortawesome/fontawesome-free/svgs/solid/times.svg");
                    padding-right: 1.5rem;
                    background-repeat: no-repeat;
                    background-size: contain;
                    background-position: right;
                }
                &:not(.error):focus {
                    background: url("../../../node_modules/@fortawesome/fontawesome-free/svgs/solid/check.svg");
                    padding-right: 1.5rem;
                    background-repeat: no-repeat;
                    background-size: contain;
                    background-position: right;
                }
            }
        }
        .ti-tag {
            border-radius: 4px;
            font-size: 0.8rem;
            font-weight: 400;
        }
        &.tag-area {
            background-color: transparent;
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

.tags-display {
    // adds in a graphic in place of the text input
    @include newTagHoverButton();

    // match bootstrap tag styles/colors
    @include matchBootstrapStyling();

    // display-only tags
    &.disabled {
        @include forDisplayOnly();
    }
}
</style>

<template>
    <div class="position-relative">
        <TagEditor
            class="border-0 bg-transparent shadow-none m-0 p-0"
            v-model="localTags"
            :query.sync="localQuery"
            separator=" ,;"
            tag-pills
            remove-on-delete
            placeholder="Add Tags..."
            size="sm"
        >
            <!-- pass through -->
            <template v-slot:tag="tagSlotData">
                <slot name="tag" v-bind="tagSlotData"></slot>
            </template>
        </TagEditor>

        <SuggestionList
            v-show="suggestions.length"
            class="position-absolute w-100"
            style="z-index: 1000;"
            :suggestions="suggestions"
            @onSelect="$emit('selectSuggestion', $event)"
        />
    </div>
</template>

<script>
import TagEditor from "./TagEditor";
import SuggestionList from "./SuggestionList";

export default {
    components: {
        TagEditor,
        SuggestionList,
    },
    props: {
        tags: { type: Array, required: true },
        suggestions: { type: Array, required: true },
        query: { type: String, required: false, default: "" },
    },
    computed: {
        localTags: {
            get() {
                return this.tags;
            },
            set(val) {
                this.$emit("update:tags", val);
            },
        },
        localQuery: {
            get() {
                return this.query;
            },
            set(val) {
                this.$emit("update:query", val);
            },
        },
    },
};
</script>

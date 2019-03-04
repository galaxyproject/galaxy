<!--
Wraps up existing functionality for community/indvidual tags. The component
wraps the more general "GalaxyTags".

I expect that "StandardTags" will go away one day as we move more of the site
into nested components/views which will implement "GalaxyTags"  with appropriate
context-specific parameters. Until we can do that, we have to wrangle the python
parameters here.
-->

<template>
    <galaxy-tags v-model="observedTags" 
        :disabled="disabled"
        :autocomplete-items="autocompleteItems"
        @tag-click="clickHandler"
        @tag-input-changed="updateTagSearch"
        @before-adding-tag="beforeAddingTag"
        @before-deleting-tag="beforeDeletingTag"
    />
</template>

<script>
import Vue from "vue";
import VueRx from "vue-rx";
import { mapActions } from "vuex";
import { map } from "rxjs/operators";
import GalaxyTags from "./GalaxyTags";
import { redirectToUrl } from "utils/redirect";
import { buildTagService } from "./tagService";
import { diffTags } from "./model";

Vue.use(VueRx);

export default {
    components: {
        GalaxyTags
    },
    props: {
        tags: { type: Array, required: false, default: () => [] },

        // currently we're passing in the click handler name as a property, and
        // that property is still defined by python, so this will have to stay
        // for a little bit.
        tagClickFn: { type: String, required: false, default: "" },

        // used with community_tag_click option
        clickUrl: { type: String, required: false, default: "" },

        // tag service params (TODO: should inject the service in as a property
        // instead of constructing it in here from the props)
        id: { type: String, required: true },
        itemClass: { type: String, required: true },
        context: { type: String, required: false, default: "" },
        debounceInterval: { type: Number, required: false, default: 150 },

        // allows user to add tags
        disabled: { type: Boolean, required: false, default: false }
    },
    computed: {
        observedTags: {
            get() {
                return this.$store.getters.getTagsById(this.id);
            },
            set(newTags) {
                this.updateTags({ 
                    key: this.id, 
                    tags: newTags 
                });
            },
        },
        tagService() {
            return buildTagService(this.$props);
        }
    },
    subscriptions() {
        return {
            // return search result tags without the ones we've already selected
            autocompleteItems: this.tagService.autocompleteOptions.pipe(
                map(resultTags => diffTags(resultTags, this.tags))
            )
        };
    },
    methods: {
        clickHandler(tag) {
            if (undefined !== this[this.tagClickFn]) {
                this[this.tagClickFn](tag);
            }
        },
        
        add_tag_to_grid_filter(tag) {
            this.$store.dispatch("toggleSearchTag", tag);
        },

        community_tag_click(tag) {
            // I made this match the existing behavior, but I am not clear on
            // the reason why this link redirects to a raw json page
            let suffix = tag.value ? `:${tag.value}` : "";
            let href = `${this.clickUrl}?f-tags=${tag.text}${suffix}`;
            redirectToUrl(href);
        },

        // Hooks to save/delete tag to server before updating UI

        beforeAddingTag({ tag, addTag }) {
            this.tagService
                .save(tag)
                .then(() => addTag(tag))
                .catch(err => console.warn("unable to save tag", err));
        },

        beforeDeletingTag({ tag, deleteTag }) {
            this.tagService
                .delete(tag)
                .then(result => deleteTag(tag))
                .catch(err => console.warn("Unable to delete tag", err));
        },

        // Set search value on tag service input proprety and eventually search
        // results will appear on the tagService.autocompleteOptions observable
        // object which is subscribed to above

        updateTagSearch(searchTxt) {
            this.tagService.autocompleteSearchText = searchTxt;
        },

        ...mapActions(["updateTags"])
    },
    created() {
        // initialize store with loaded values
        this.updateTags({ 
            key: this.id, 
            tags: this.tags 
        });
    }
};
</script>

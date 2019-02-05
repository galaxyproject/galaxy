<template>
    <galaxy-tags v-model="tags" 
        :use-toggle-link="false"
        :disabled="disabled"
        :autocomplete-items="autocompleteItems"
        @tag-input-changed="loadAutoCompleteItems"
    />
</template>

<script>

import GalaxyTags from "./GalaxyTags";
import { getGalaxyInstance } from "app";
import { mapActions } from "vuex";

export default {
    components: {
        GalaxyTags
    },
    props: {
        model: { type: Object, required: true },
        disabled: { type: Boolean, required: false, default: false }
    },
    data() {
        return {
            autocompleteItems: []
        }
    },
    computed: {
        tags: {
            get() {
                return this.$store.getters.getTagsById(this.model.id);
            },
            set(tags) {
                this.model.save({ tags }).then(newModel => {
                    this.updateTags({ key: newModel.id, tags: newModel.tags });
                })
            }
        }
    },
    methods: {
        loadAutoCompleteItems(txt) {
            let Galaxy = getGalaxyInstance();
            this.autocompleteItems = Galaxy.user.get("tags_used")
                .filter(label => label.includes(txt));
        },
        ...mapActions(["updateTags"])
    },
    created() {
        this.updateTags({ 
            key: this.model.id, 
            tags: this.model.attributes.tags 
        });
    }
}

// list of previously used tags in the dropdown
function updateGalaxyUserTags(tags = []) {
    let Galaxy = getGalaxyInstance();
    let userTags = new Set(Galaxy.user.get("tags_used"));
    tags.foreach(tag => userTags.add(tag));
    Galaxy.user.set("tags_user", Array.from(userTags).sort());
}

</script>

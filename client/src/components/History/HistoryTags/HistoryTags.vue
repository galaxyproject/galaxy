<template>
    <HistoryTagProvider :history="history" v-slot="{ tags, saveTag, saveTags }">
        <SuggestionProvider
            :query="tagInputText"
            :available="available"
            :selected="tags"
            v-slot="{ 
                options,
                activeSuggestion = { value: null },
                nextSuggestion, 
                lastSuggestion 
            }"
        >
            <Tags
                :tags="tags"
                @update:tags="saveTags"
                :suggestions="options"
                :query.sync="tagInputText"
                @keyup.native.down="nextSuggestion"
                @keyup.native.up="lastSuggestion"
                @keyup.native.enter="saveTag(activeSuggestion.value)"
                @selectSuggestion="(sugg) => saveTag(sugg.value)"
            >
                <template v-slot:tag="{ tag, removeTag }">
                    <colored-tag class="mr-1 mb-1" :tag="tag" @remove="removeTag(tag)" />
                </template>
            </Tags>
        </SuggestionProvider>
    </HistoryTagProvider>
</template>

<script>
import HistoryTagProvider from "./HistoryTagProvider";
import { Tags, SuggestionProvider, ColoredTag } from "./Tags";

export default {
    components: {
        Tags,
        HistoryTagProvider,
        SuggestionProvider,
        ColoredTag,
    },
    props: {
        history: { type: Object, required: true },
    },
    data() {
        return {
            tagInputText: "",
            available: [],
        };
    },
    async created() {
        this.available = ["America", "Asia", "Africa"];
    },
};
</script>

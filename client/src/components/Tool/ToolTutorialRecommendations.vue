<script setup lang="ts">
import { faCaretDown } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, reactive, ref, set } from "vue";

import { useToolTrainingMaterial } from "@/composables/toolTrainingMaterial";

import GButton from "@/components/BaseComponents/GButton.vue";
import GCollapse from "@/components/BaseComponents/GCollapse.vue";
import Heading from "@/components/Common/Heading.vue";
import ExternalLink from "@/components/ExternalLink.vue";

const props = defineProps<{
    name: string;
    id: string;
    version: string;
    owner?: string;
}>();

const { trainingAvailable, trainingCategories, tutorialDetails, allTutorialsUrl, versionAvailable } =
    useToolTrainingMaterial(props.id, props.name, props.version, props.owner);

const mainOpen = ref(false);
const categoryOpen = reactive<Record<string, boolean>>({});

function tutorialsInCategory(category: string) {
    return tutorialDetails.value.filter((tut) => tut.category === category);
}

const tutorialText = computed(() => {
    if (tutorialDetails.value.length > 1) {
        return `There are ${tutorialDetails.value.length} tutorials available which use this tool.`;
    } else {
        return "There is 1 tutorial available which uses this tool.";
    }
});

function toggleCategory(category: string) {
    set(categoryOpen, category, !categoryOpen[category]);
}
</script>

<template>
    <div v-if="trainingAvailable" class="mt-2 mb-4">
        <Heading v-localize h2 separator bold size="sm">Tutorials</Heading>

        <p>
            {{ tutorialText }}
            <span v-if="versionAvailable"> These tutorials include training for the current version of the tool. </span>

            <ExternalLink v-if="allTutorialsUrl" :href="allTutorialsUrl">
                View all tutorials referencing this tool.
            </ExternalLink>
        </p>

        <GButton class="ui-link" transparent inline color="blue" @click="mainOpen = !mainOpen">
            <b>
                Tutorials available in {{ trainingCategories.length }}
                {{ trainingCategories.length > 1 ? "categories" : "category" }}
            </b>
            <FontAwesomeIcon :icon="faCaretDown" />
        </GButton>
        <GCollapse v-model="mainOpen">
            <div v-for="category in trainingCategories" :key="category">
                <GButton class="ui-link ml-3" transparent inline color="blue" @click="toggleCategory(category)">
                    {{ category }} ({{ tutorialsInCategory(category).length }})
                    <FontAwesomeIcon :icon="faCaretDown" />
                </GButton>
                <GCollapse :visible="!!categoryOpen[category]">
                    <ul class="d-flex flex-column my-1">
                        <li v-for="tutorial in tutorialsInCategory(category)" :key="tutorial.title">
                            <ExternalLink :href="tutorial.url.toString()" class="ml-2">
                                {{ tutorial.title }}
                            </ExternalLink>
                        </li>
                    </ul>
                </GCollapse>
            </div>
        </GCollapse>
    </div>
</template>

<style scoped lang="scss">
// GButton's transparent-blue hover repaints the label near-white, and `.ui-link` keeps
// the background transparent, so without this the toggles vanish on hover. The extra
// `.g-*` classes are not decoration: they are what lifts this rule above
// `.g-button.g-transparent:not(.g-pressed).g-blue:hover`.
.ui-link.g-button.g-transparent.g-blue:not(.g-pressed) {
    &:hover,
    &:focus-visible {
        color: var(--color-blue-700);
        text-decoration: underline;
    }
}
</style>

<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCaretDown } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, BCollapse } from "bootstrap-vue";
import slugify from "slugify";
import { computed } from "vue";

import { useToolTrainingMaterial } from "@/composables/toolTrainingMaterial";
import { useUid } from "@/composables/utils/uid";

import Heading from "@/components/Common/Heading.vue";
import ExternalLink from "@/components/ExternalLink.vue";

const props = defineProps<{
    name: string;
    id: string;
    version: string;
    owner?: string;
}>();

library.add(faCaretDown);

const { trainingAvailable, trainingCategories, tutorialDetails, allTutorialsUrl, versionAvailable } =
    useToolTrainingMaterial(props.id, props.name, props.version, props.owner);

const collapseId = useUid("collapse-");

function idForCategory(category: string) {
    return `${collapseId.value}-${slugify(category)}`;
}

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
</script>

<template>
    <div v-if="trainingAvailable" class="mt-2 mb-4">
        <Heading h2 separator bold size="sm">Tutorials</Heading>

        <p>
            {{ tutorialText }}
            <span v-if="versionAvailable"> These tutorials include training for the current version of the tool. </span>

            <ExternalLink v-if="allTutorialsUrl" :href="allTutorialsUrl">
                View all tutorials referencing this tool.
            </ExternalLink>
        </p>

        <BButton v-b-toggle="collapseId" class="ui-link">
            <b>
                Tutorials available in {{ trainingCategories.length }}
                {{ trainingCategories.length > 1 ? "categories" : "category" }}
            </b>
            <FontAwesomeIcon icon="caret-down" />
        </BButton>
        <BCollapse :id="collapseId">
            <div v-for="category in trainingCategories" :key="category">
                <BButton v-b-toggle="idForCategory(category)" class="ui-link ml-3">
                    {{ category }} ({{ tutorialsInCategory(category).length }})
                    <FontAwesomeIcon icon="caret-down" />
                </BButton>
                <BCollapse :id="idForCategory(category)">
                    <ul class="d-flex flex-column my-1">
                        <li v-for="tutorial in tutorialsInCategory(category)" :key="tutorial.title">
                            <ExternalLink :href="tutorial.url.toString()" class="ml-2">
                                {{ tutorial.title }}
                            </ExternalLink>
                        </li>
                    </ul>
                </BCollapse>
            </div>
        </BCollapse>
    </div>
</template>

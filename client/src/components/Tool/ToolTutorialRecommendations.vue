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
        return `有${tutorialDetails.value.length}个教程可用于此工具。`;
    } else {
        return "有1个教程可用于此工具。";
    }
});
</script>

<template>
    <div v-if="trainingAvailable" class="mt-2 mb-4">
        <Heading h2 separator bold size="sm">教程</Heading>

        <p>
            {{ tutorialText }}
            <span v-if="versionAvailable"> 这些教程包含当前版本工具的培训内容。</span>

            <ExternalLink v-if="allTutorialsUrl" :href="allTutorialsUrl">
                查看所有引用此工具的教程。
            </ExternalLink>
        </p>

        <BButton v-b-toggle="collapseId" class="ui-link">
            <b>
                {{ trainingCategories.length }}个
                {{ trainingCategories.length > 1 ? "类别" : "类别" }}的可用教程
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

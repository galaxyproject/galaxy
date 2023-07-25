<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faBuilding, faExternalLinkAlt } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";

const props = defineProps({
    grant: {
        type: Object,
        required: true,
    },
    hoverPlacement: {
        type: String,
        default: "left",
    },
});

library.add(faExternalLinkAlt, faBuilding);

type item = {
    attribute: string;
    value: string;
};

const name = computed<string>(() => props.grant.name);
const items: any = [];
for (const key in props.grant) {
    if (key == "class") {
        continue;
    }
    items.push({ attribute: key, value: props.grant[key] });
};

const implicitMicrodataProperties = ["name", "description", "url", "identifier"];

const explicitMetaAttributes = computed(() => {
    return items.filter((i: item) => implicitMicrodataProperties.includes(i.attribute));
});
</script>

<template>
    <span itemprop="funding" itemscope itemtype="https://schema.org/Grant">
        <b-button ref="button">
            <FontAwesomeIcon icon="money-bill" />
        </b-button>
        <b-popover triggers="click blur" :placement="hoverPlacement" :target="$refs['button'] || 'works-lazily'"
            title="Grant">
            <b-table striped :items="items"> </b-table>
        </b-popover>
        <span v-if="name">
            <span itemprop="name">{{ name }}</span>
        </span>
        <span v-else-if="props.grant.description" itemprop="description">
            {{ props.grant.description }}
        </span>
        <a v-if="props.grant.url" v-b-tooltip.hover title="Grant URL" :href="props.grant.url" target="_blank">
            <link itemprop="url" :href="props.grant.url" />
            <FontAwesomeIcon icon="external-link-alt" />
        </a>
        <meta v-for="attribute in explicitMetaAttributes" :key="attribute.attribute" :itemprop="attribute.attribute"
            :content="attribute.value" />
        <slot name="buttons"></slot>
    </span>
</template>

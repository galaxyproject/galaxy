<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCoins, faExternalLinkAlt } from "@fortawesome/free-solid-svg-icons";
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

library.add(faExternalLinkAlt, faCoins);

type item = {
    attribute: string;
    value: string;
};

const items = computed(() => {
    const items: item[] = [];
    for (const key in props.grant) {
        if (key == "class") {
            continue;
        }
        items.push({ attribute: key, value: props.grant[key] });
    }
    return items;
});

const implicitMicrodataProperties = ["name", "description", "url", "identifier"];

const explicitMetaAttributes = computed(() => {
    return items.value.filter((i: item) => implicitMicrodataProperties.includes(i.attribute));
});
</script>

<template>
    <span itemprop="funding" itemscope itemtype="https://schema.org/Grant">
        <b-button ref="button" v-b-modal.funding-details class="py-0 px-1" size="sm" variant="link" title="Grant details">
            <FontAwesomeIcon icon="coins" fixed-width />
        </b-button>
        <b-modal id="funding-details" title="Grant" hide-footer>
            <b-table striped :items="items"> </b-table>
        </b-modal>
        <span v-if="props.grant.name">
            {{ props.grant.name }}
        </span>
        <span v-if="props.grant.description">
            - {{ props.grant.description }}
        </span>
        <span v-if="props.grant.identifier">
            ({{ props.grant.identifier }})
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

<script setup lang="ts">
import { faExternalLinkAlt, faEye, faLink, faSitemap } from "@fortawesome/free-solid-svg-icons";
import { computed } from "vue";
import { useRouter } from "vue-router/composables";

import { getFullAppUrl } from "@/app/utils";
import { Toast } from "@/composables/toast";
import type { ToolSection } from "@/stores/toolStore";
import { copy } from "@/utils/clipboard";

import type { CardAction, CardBadge, Title } from "../Common/GCard.types";

import GCard from "../Common/GCard.vue";

const router = useRouter();

const props = defineProps<{
    ontology: ToolSection;
    header?: boolean;
    routable?: boolean;
}>();

const title = computed<Title>(() => {
    if (props.routable) {
        return {
            label: props.ontology.name,
            title: props.ontology.name,
            handler: () => {
                router.push(`/tools/list?ontology="${props.ontology.id}"`);
            },
        };
    } else {
        return props.ontology.name;
    }
});

const badges = computed<CardBadge[]>(() => {
    return [
        {
            id: "ontology-id",
            label: props.ontology.id,
            title: "Copy the EDAM id for this ontology",
            class: `edam-ontology-badge ${props.ontology.id.includes("operation") ? "operation" : "topic"}`,
            visible: true,
            icon: faSitemap,
            handler: () => {
                copy(props.ontology.id);
                Toast.success(`EDAM ID "${props.ontology.id}" copied to clipboard`);
            },
        },
    ];
});

const primaryActions = computed<CardAction[]>(() => {
    const actions: CardAction[] = [];
    if (props.routable) {
        actions.push({
            id: "tools-list-ontology-view-link",
            label: "View Tools",
            icon: faEye,
            title: "View tools in this ontology",
            to: `/tools/list?ontology="${props.ontology.id}"`,
        });
    }
    return actions;
});

const secondaryActions = computed<CardAction[]>(() => {
    const actions: CardAction[] = [];
    const ontologyId = props.ontology.id;
    const ontologyName = props.ontology.name;
    actions.push({
        id: "tools-list-ontology-filter-link",
        label: "Link to these results",
        icon: faLink,
        title: "Copy link to these results",
        variant: "outline-primary",
        handler: () => {
            const link = getFullAppUrl(`tools/list?ontology="${ontologyId}"`);
            copy(link);
            Toast.success(`Link to ontology "${ontologyName} (${ontologyId})" copied to clipboard`);
        },
    });
    if (props.ontology.links && "edam_browser" in props.ontology.links) {
        actions.push({
            id: "ontology-link",
            label: "EDAM Browser",
            icon: faExternalLinkAlt,
            title: "View in EDAM Browser",
            variant: "outline-primary",
            href: props.ontology.links.edam_browser,
            externalLink: true,
        });
    }
    return actions;
});
</script>

<template>
    <GCard
        v-if="props.ontology?.description"
        :current="props.header"
        :badges="badges"
        :primary-actions="primaryActions"
        :secondary-actions="secondaryActions"
        :description="props.ontology.description"
        full-description
        :title="title">
        <template v-slot:update-time>
            <i v-if="props.ontology.tools"> {{ props.ontology.tools.length }} tools in this ontology </i>
        </template>
    </GCard>
</template>

<script setup lang="ts">
import { computed } from "vue";

import type { ObjectStoreBadgeType } from "@/api/objectStores.templates";

import { type ObjectStoreTemplateSummary } from "./types";

import ConfigurationMarkdown from "@/components/ObjectStore/ConfigurationMarkdown.vue";
import ObjectStoreBadges from "@/components/ObjectStore/ObjectStoreBadges.vue";
import ObjectStoreTypeSpan from "@/components/ObjectStore/ObjectStoreTypeSpan.vue";

interface Props {
    template: ObjectStoreTemplateSummary;
}

const props = defineProps<Props>();
const badges = computed<ObjectStoreBadgeType[]>(() => props.template.badges);
const objectStoreType = computed(() => props.template.type);
</script>

<template>
    <div>
        <ObjectStoreBadges :badges="badges" size="lg" />
        <div>This template produces a Galaxy storage of type <ObjectStoreTypeSpan :type="objectStoreType" />.</div>
        <ConfigurationMarkdown :markdown="template.description || ''" :admin="true" />
    </div>
</template>

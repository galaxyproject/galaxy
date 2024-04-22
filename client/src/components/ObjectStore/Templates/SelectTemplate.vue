<script lang="ts" setup>
import type { ObjectStoreTemplateSummaries } from "./types";

import TemplateSummaryPopover from "./TemplateSummaryPopover.vue";

interface SelectTemplateProps {
    templates: ObjectStoreTemplateSummaries;
}

defineProps<SelectTemplateProps>();

const selectText =
    "Select storage location template to create new storage location with. These templates are configured by your Galaxy administrator.";

const emit = defineEmits<{
    (e: "onSubmit", id: string): void;
}>();

async function handleSubmit(templateId: string) {
    emit("onSubmit", templateId);
}
</script>

<template>
    <div>
        <b-row>
            <b-col cols="7">
                <b-button-group vertical size="lg" style="width: 100%">
                    <b-button
                        v-for="template in templates"
                        :id="`object-store-template-button-${template.id}`"
                        :key="template.id"
                        class="object-store-template-select-button"
                        :data-template-id="template.id"
                        @click="handleSubmit(template.id)"
                        >{{ template.name }}
                    </b-button>
                </b-button-group>
            </b-col>
            <b-col cols="5">
                <p v-localize style="float: right">
                    {{ selectText }}
                </p>
            </b-col>
        </b-row>
        <TemplateSummaryPopover
            v-for="template in templates"
            :key="template.id"
            :target="`object-store-template-button-${template.id}`"
            :template="template" />
    </div>
</template>

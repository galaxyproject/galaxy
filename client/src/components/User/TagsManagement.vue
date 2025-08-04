<script setup lang="ts">
import { faClock, faTrash } from "@fortawesome/free-solid-svg-icons";
import { storeToRefs } from "pinia";

import type { CardAction } from "@/components/Common/GCard.types";
import { useUserTagsStore } from "@/stores/userTagsStore";

import BreadcrumbHeading from "@/components/Common/BreadcrumbHeading.vue";
import GCard from "@/components/Common/GCard.vue";

const userTagsStore = useUserTagsStore();
const { userTagsDetail } = storeToRefs(userTagsStore);

function getPrimaryActions(t: { tag: string }): CardAction[] {
    return [
        {
            id: "delete-tag",
            label: "",
            icon: faTrash,
            title: "Delete Tag",
            variant: "outline-danger",
            handler: () => {
                // userTagsStore.onTagDelete(t.tag);
            },
        },
    ];
}
</script>

<template>
    <div>
        <BreadcrumbHeading :items="[{ title: 'User Preferences', to: '/user' }, { title: 'Manage Tags' }]" />

        <div class="d-flex flex-wrap">
            <GCard
                v-for="tag in userTagsDetail"
                :key="tag.tag"
                :title="tag.tag"
                grid-view
                :primary-actions="getPrimaryActions(tag)"
                :update-time="new Date(tag.lastUsed).toISOString()"
                :update-time-icon="faClock"
                update-time-title="Last used" />
        </div>
    </div>
</template>

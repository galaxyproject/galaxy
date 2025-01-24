<script setup lang="ts">
import UtcDate from "@/components/UtcDate.vue"

import { type FragmentType, useFragment } from "@/gql/fragment-masking"
import { goToRepository } from "@/router"
import { CreateFragment } from "@/gqlFragements"

const props = defineProps<{
    creation: FragmentType<typeof CreateFragment>
}>()
const creation = useFragment(CreateFragment, props.creation)

function onClick() {
    goToRepository(creation.encodedId)
}
</script>

<template>
    <q-item clickable v-ripple @click="onClick">
        <q-item-section v-if="creation">
            <q-item-label>{{ creation.name }}</q-item-label>
            <q-item-label caption>
                <div>
                    {{ creation.user.username }}/{{ creation.name }} created
                    <utc-date :date="creation.createTime" mode="elapsed" />
                </div>
            </q-item-label>
        </q-item-section>
    </q-item>
</template>

<script setup lang="ts">
import UtcDate from "@/components/UtcDate.vue"
import { goToRepository } from "@/router"
import { type FragmentType, useFragment } from "@/gql/fragment-masking"
import { UpdateFragment } from "@/gqlFragements"

const props = defineProps<{
    update: FragmentType<typeof UpdateFragment>
}>()
const update = useFragment(UpdateFragment, props.update)
</script>

<template>
    <q-item clickable v-ripple @click="goToRepository(update.encodedId)">
        <q-item-section v-if="update">
            <q-item-label>{{ update.name }}</q-item-label>
            <q-item-label caption>
                <div>
                    {{ update.user.username }}/{{ update.name }} updated
                    <utc-date :date="update.updateTime" mode="elapsed" />
                </div>
            </q-item-label>
        </q-item-section>
    </q-item>
</template>

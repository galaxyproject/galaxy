<script setup lang="ts">
import UtcDate from "@/components/UtcDate.vue"

import type { Repository } from "@/api"

import { goToRepository } from "@/router"

interface Props {
    repository: Repository
}

const props = defineProps<Props>()

function onClick() {
    goToRepository(props.repository.id)
}
</script>

<template>
    <q-item clickable v-ripple @click="onClick">
        <q-item-section v-if="repository">
            <q-item-label>{{ repository.name }}</q-item-label>
            <q-item-label caption>
                <div>
                    {{ repository.owner }}/{{ repository.name }} created
                    <utc-date :date="repository.create_time" mode="elapsed" />
                </div>
            </q-item-label>
        </q-item-section>
    </q-item>
</template>

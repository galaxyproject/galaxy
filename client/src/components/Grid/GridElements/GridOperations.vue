<script setup lang="ts">
import type { FieldOperations } from "@/components/Grid/configs/types";

interface Props {
    title: string;
    operations: FieldOperations;
}

defineProps<Props>();
</script>

<template>
    <span>
        <b-link id="grid-operations" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
            <icon icon="caret-down" class="fa-lg" />
            <span class="font-weight-bold">{{ title }}</span>
        </b-link>
        <div class="dropdown-menu" aria-labelledby="dataset-dropdown">
            <a
                v-for="(operation, operationIndex) in operations"
                :key="operationIndex"
                class="dropdown-item"
                @click.prevent="$emit('execute', operation)">
                <span v-localize>{{ operation.title }}</span>
            </a>
        </div>
    </span>
</template>

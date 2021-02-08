<template>
    <b-dropdown no-caret right variant="link" size="sm" boundary="window" toggle-class="p-1">
        <template v-slot:button-content>
            <i class="fas fa-trash" />
            <span class="sr-only" v-localize>Delete Collection</span>
        </template>

        <b-dropdown-item @click.stop="$emit('delete')">
            <span v-localize>Delete Collection Only</span>
        </b-dropdown-item>

        <b-dropdown-item @click.stop="$emit('delete', { recursive: true })">
            <span v-localize>Delete Contained Datasets</span>
        </b-dropdown-item>

        <b-dropdown-item @click.stop="$emit('delete', { recursive: true, purge: true })">
            <span v-localize>Purge Contained Datasets</span>
        </b-dropdown-item>
    </b-dropdown>
</template>

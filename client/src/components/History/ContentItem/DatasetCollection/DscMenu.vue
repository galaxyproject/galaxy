<template>
    <PriorityMenu :starting-height="27">
        <PriorityMenuItem>
            <b-dropdown no-caret right variant="link" size="sm" boundary="window" toggle-class="p-1">
                <template v-slot:button-content>
                    <i class="fas fa-trash" />
                    <span class="sr-only">Delete Collection</span>
                </template>

                <b-dropdown-item @click.stop="$emit('deleteCollection')"> Delete Collection Only </b-dropdown-item>

                <b-dropdown-item @click.stop="$emit('deleteCollection', { recursive: true })">
                    Delete Contained Datasets
                </b-dropdown-item>

                <b-dropdown-item @click.stop="$emit('deleteCollection', { recursive: true, purge: true })">
                    Purge Contained Datasets
                </b-dropdown-item>
            </b-dropdown>
        </PriorityMenuItem>
        <PriorityMenuItem>
            <b-dropdown no-caret right variant="link" size="sm" boundary="window" toggle-class="p-1">
                <template v-slot:button-content>
                    <i class="fa fa-pencil" />
                    <span class="sr-only">Edit Collection</span>
                </template>

                <b-dropdown-item @click.stop="$emit('deleteCollection', { recursive: true })">
                    Edit Database/Build
                </b-dropdown-item>

                <b-dropdown-item @click.stop="$emit('deleteCollection', { recursive: true })">
                    Convert Datatype 
                </b-dropdown-item>

            </b-dropdown>
        </PriorityMenuItem>
    </PriorityMenu>
</template>

<template>
    <div>LibraryPermissions {{ libraryId }}</div>
</template>

<script>
export default {
    props: {
        libraryId: { type: String, required: true },
    },
};
</script>

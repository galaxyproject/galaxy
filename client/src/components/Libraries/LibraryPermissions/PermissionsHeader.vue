<template>
    <div>
        <div v-if="name">
            <div>
                <div class="header text-center">{{ name }}</div>
            </div>
        </div>
        <LibraryPermissionsWarning :is_admin="is_admin" />
        <hr class="my-4" />
    </div>
</template>

<script>
import { getGalaxyInstance } from "app";
import LibraryPermissionsWarning from "components/Libraries/LibraryFolder/LibraryFolderPermissions/LibraryPermissionsWarning";

export default {
    components: {
        LibraryPermissionsWarning,
    },
    props: {
        name: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            is_admin: getGalaxyInstance().user.attributes.is_admin,
        };
    },
};
</script>

<style scoped>
.header {
    font-size: 25px;
}
</style>

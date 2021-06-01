<template>
    <div>
        <div v-if="name">
            <b-button variant="primary" title="back to parent folder" :to="{ path: `${this.path}` }">
                <font-awesome-icon icon="angle-double-left" />
            </b-button>
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
import LibraryPermissionsWarning from "components/Libraries/LibraryFolder/LibraryFolderPermissions/LibraryPermissionsWarning.vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

export default {
    props: {
        name: {
            type: String,
            required: true,
        },
        path: {
            type: String,
            required: true,
        },
    },
    components: {
        LibraryPermissionsWarning,
        FontAwesomeIcon,
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
    font-size: 45px;
}
</style>

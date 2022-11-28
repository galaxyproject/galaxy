<template>
    <BaseList
        :fields="fields"
        icon="far fa-trash-alt"
        tooltip="Reset"
        plural="metadata entries"
        success="successful"
        :getter="getter"
        :setter="setter" />
</template>
<script>
import BaseList from "./BaseList";
import { getInstalledRepositories, resetRepositoryMetadata } from "./AdminServices";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faTrashAlt } from "@fortawesome/free-regular-svg-icons";

library.add(faTrashAlt);

export default {
    components: {
        BaseList,
    },
    data() {
        return {
            fields: [
                { key: "execute", label: "Reset" },
                { key: "name", label: "Metadata", sortable: true },
                { key: "owner", sortable: true },
                { key: "ctx_rev", label: "Revision" },
            ],
            getter: getInstalledRepositories,
            setter: resetRepositoryMetadata,
        };
    },
};
</script>

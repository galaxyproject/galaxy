<template>
    <BaseList
        :fields="fields"
        icon="fa fa-trash-o"
        tooltip="Reset"
        plural="metadata entries"
        success="successful"
        :getter="getter"
        :setter="setter" />
</template>
<script>
import { getInstalledRepositories, resetRepositoryMetadata } from "./AdminServices";
import BaseList from "./BaseList";

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

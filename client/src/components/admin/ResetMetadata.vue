<template>
    <BaseList
        :fields="fields"
        icon="fa fa-trash-o"
        tooltip="重置"
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
                { key: "execute", label: "重置" },
                { key: "name", label: "元数据", sortable: true },
                { key: "owner", sortable: true },
                { key: "ctx_rev", label: "修订" },
            ],
            getter: getInstalledRepositories,
            setter: resetRepositoryMetadata,
        };
    },
};
</script>

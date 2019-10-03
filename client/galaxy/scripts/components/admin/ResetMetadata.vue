<template>
    <BaseList
        :itemsAttributes=itemsAttributes
        iconClass="fa fa-trash-o"
        iconTooltip="Reset"
        itemsPlural="metadata entries"
        itemsSuccess="successful"
        :serviceRequest="serviceRequest"
        :serviceExecute="serviceExecute"
    />
</template>
<script>
import BaseList from "./BaseList";
import { getInstalledRepositories, resetRepositoryMetadata } from "./AdminServices.js";

export default {
    components: {
        BaseList
    },
    data() {
        return {
            itemsAttributes: [
                { key: "execute", label: "Reset" },
                { key: "name", label: "Metadata", sortable: true },
                { key: "owner", sortable: true },
                { key: "ctx_rev", label: "Revision" }
            ]
        };
    },
    methods: {
        serviceRequest: function() {
            return getInstalledRepositories();
        },
        serviceExecute: function(ids) {
            return resetRepositoryMetadata(ids);
        }
    }
};
</script>

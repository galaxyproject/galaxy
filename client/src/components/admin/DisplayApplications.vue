<template>
    <div aria-labelledby="display-applications-heading">
        <h1 id="display-applications-heading" class="h-lg">Display Applications</h1>
        <BaseList
            :fields="fields"
            icon="fa fa-sync"
            tooltip="Refresh"
            plural="display applications"
            success="reloaded"
            :getter="getter"
            :setter="setter" />
    </div>
</template>

<script>
import { getDisplayApplications, reloadDisplayApplications } from "./AdminServices";

import BaseList from "@/components/admin/BaseList.vue";

export default {
    components: {
        BaseList,
    },
    data() {
        return {
            fields: [
                { key: "execute", label: "Refresh" },
                { key: "name", label: "Name", sortable: true },
                { key: "id", label: "ID", sortable: true },
                { key: "version", label: "Version" },
                { key: "links", label: "Links" },
            ],
            getter: getDisplayApplications,
            setter: reloadDisplayApplications,
        };
    },
};
</script>

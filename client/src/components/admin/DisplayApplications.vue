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
import BaseList from "./BaseList";
import { getDisplayApplications, reloadDisplayApplications } from "./AdminServices";

export default {
    components: {
        BaseList,
    },
    data() {
        return {
            fields: [
                { key: "execute", label: "Refresh" },
                { key: "name", sortable: true },
                { key: "id", sortable: true },
                { key: "version" },
                { key: "links" },
            ],
            getter: getDisplayApplications,
            setter: reloadDisplayApplications,
        };
    },
};
</script>

<template>
    <div aria-labelledby="display-applications-heading">
        <h1 id="display-applications-heading" class="h-lg">显示应用</h1>
        <BaseList
            :fields="fields"
            icon="fa fa-sync"
            tooltip="刷新"
            plural="显示应用"
            success="reloaded"
            :getter="getter"
            :setter="setter" />
    </div>
</template>
<script>
import { getDisplayApplications, reloadDisplayApplications } from "./AdminServices";
import BaseList from "./BaseList";

export default {
    components: {
        BaseList,
    },
    data() {
        return {
            fields: [
                { key: "execute", label: "刷新" },
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

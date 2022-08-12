<template>
    <div id="columns">
        <div id="center">
            <div class="center-container m-2">
                <router-view :key="$route.fullPath" />
            </div>
        </div>
    </div>
</template>
<script>
import { getGalaxyInstance } from "app";
import SidePanel from "components/Panels/SidePanel";

export default {
    components: {
        SidePanel,
    },
    methods: {
        getToolBox() {
            //<SidePanel side="left" :currentPanel="getAdminBox()" />
            //return ToolBox;
        },
    },
};
</script>

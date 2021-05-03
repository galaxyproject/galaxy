<template>
    <CurrentUser v-slot="{ user }">
        <UserHistories v-if="user" :user="user" v-slot="{ currentHistory }">
            <PluginList v-if="currentHistory.id" :dataset-id="datasetId" :current-history-id="currentHistory.id" />
        </UserHistories>
    </CurrentUser>
</template>

<script>
import CurrentUser from "components/providers/CurrentUser";
import { UserHistories } from "components/History/providers";
import PluginList from "./PluginList";

export default {
    components: {
        CurrentUser,
        UserHistories,
        PluginList,
    },
    props: {
        datasetId: { type: String, required: true },
    },
};
</script>

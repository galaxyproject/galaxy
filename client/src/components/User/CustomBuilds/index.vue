<template>
    <CurrentUser v-slot="{ user }">
        <UserHistories v-if="user" :user="user" v-slot="{ currentHistory }">
            <CustomBuildsView
                v-if="currentHistory"
                :current-user-id="user.id"
                :current-history-id="currentHistory.id"
            />
        </UserHistories>
    </CurrentUser>
</template>

<script>
import CurrentUser from "components/providers/CurrentUser";
import { UserHistories } from "components/History/providers";
import CustomBuildsView from "./CustomBuildsView";

export default {
    components: {
        CurrentUser,
        UserHistories,
        CustomBuildsView,
    },
};
</script>

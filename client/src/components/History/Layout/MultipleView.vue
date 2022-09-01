<template>
    <CurrentUser v-slot="{ user }">
        <UserHistories v-if="user" v-slot="{ histories, handlers, historiesLoading, currentHistory }" :user="user">
            <b-alert v-if="historiesLoading || histories.length === 0" class="m-2" variant="info" show>
                <LoadingSpan message="Loading Histories" />
            </b-alert>

            <div v-else-if="histories.length" id="histories" class="d-flex flex-column h-100">
                <b-input-group class="m-auto w-25">
                    <DebouncedInput v-slot="{ value, input }" v-model="dataSetsFilter">
                        <b-form-input
                            size="sm"
                            :class="dataSetsFilter && 'font-weight-bold'"
                            :value="value"
                            :placeholder="'search datasets  in selected histories' | l"
                            data-description="filter text input"
                            @input="input"
                            @keyup.esc="updateDataSetsFilter('')" />
                    </DebouncedInput>
                    <b-input-group-append>
                        <b-button
                            size="sm"
                            data-description="show deleted filter toggle"
                            @click="updateDataSetsFilter('')">
                            <icon icon="times" />
                        </b-button>
                    </b-input-group-append>
                </b-input-group>

                <hr class="w-100" />

                <multiple-view-list
                    :histories="histories"
                    :data-sets-filter="dataSetsFilter"
                    :current-history="currentHistory"
                    :handlers="handlers" />
            </div>
        </UserHistories>
    </CurrentUser>
</template>

<script>
import LoadingSpan from "components/LoadingSpan";
import DebouncedInput from "components/DebouncedInput";
import CurrentUser from "components/providers/CurrentUser";
import UserHistories from "components/providers/UserHistories";
import MultipleViewList from "./MultipleViewList";

export default {
    components: {
        LoadingSpan,
        DebouncedInput,
        CurrentUser,
        UserHistories,
        MultipleViewList,
    },
    data() {
        return {
            dataSetsFilter: "",
        };
    },
    created() {
        return setTimeout(() => {
            document.getElementById("left").__vue__.hide();
        }, 1000);
    },
    methods: {
        updateDataSetsFilter(filter) {
            this.dataSetsFilter = filter;
        },
    },
};
</script>

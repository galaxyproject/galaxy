<template>
    <CurrentUser v-slot="{ user }">
        <UserHistories v-if="user" v-slot="{ histories, handlers, historiesLoading }" :user="user">
            <div v-if="!historiesLoading && histories.length" id="histories" class="d-flex flex-column h-100">
                <b-container>
                    <b-row>
                        <b-col>
                            <b-input-group>
                                <DebouncedInput v-slot="{ value, input }" v-model="historiesFilter">
                                    <b-form-input
                                        size="sm"
                                        :class="historiesFilter && 'font-weight-bold'"
                                        :value="value"
                                        :placeholder="'search histories' | localize"
                                        data-description="filter text input"
                                        @input="input"
                                        @keyup.esc="updateFilter('')" />
                                </DebouncedInput>
                                <b-input-group-append>
                                    <b-button
                                        size="sm"
                                        data-description="show deleted filter toggle"
                                        @click="updateFilter('')">
                                        <icon icon="times" />
                                    </b-button>
                                </b-input-group-append>
                            </b-input-group>
                        </b-col>

                        <b-col>
                            <b-input-group>
                                <DebouncedInput v-slot="{ value, input }" v-model="datasetsFilter">
                                    <b-form-input
                                        size="sm"
                                        :class="datasetsFilter && 'font-weight-bold'"
                                        :value="value"
                                        :placeholder="'search all datasets' | localize"
                                        data-description="filter text input"
                                        @input="input"
                                        @keyup.esc="updateFilter('')" />
                                </DebouncedInput>
                                <b-input-group-append>
                                    <b-button
                                        size="sm"
                                        data-description="show deleted filter toggle"
                                        @click="updateFilter('')">
                                        <icon icon="times" />
                                    </b-button>
                                </b-input-group-append>
                            </b-input-group>
                        </b-col>
                    </b-row>
                </b-container>

                <hr class="w-100" />

                <virtual-list
                    :data-key="'id'"
                    :data-component="MultipleViewItem"
                    :data-sources="histories"
                    :direction="'horizontal'"
                    :extra-props="{ handlers, onViewCollection }"
                    :item-style="{ minWidth: '15rem', maxWidth: '15rem' }"
                    item-class="d-flex mx-1"
                    class="flex-grow-1"
                    style="overflow: auto hidden"
                    wrap-class="row container flex-nowrap h-100 m-0">
                </virtual-list>
            </div>
            <b-alert v-else class="m-2" variant="info" show>
                <LoadingSpan message="Loading Histories" />
            </b-alert>
        </UserHistories>
    </CurrentUser>
</template>

<script>
import MultipleViewItem from "./MultipleViewItem";
import LoadingSpan from "components/LoadingSpan";
import VirtualList from "vue-virtual-scroll-list";
import DebouncedInput from "components/DebouncedInput";
import CurrentUser from "components/providers/CurrentUser";
import UserHistories from "components/providers/UserHistories";

export default {
    components: {
        LoadingSpan,
        VirtualList,
        DebouncedInput,
        CurrentUser,
        UserHistories,
    },
    data() {
        return { MultipleViewItem: MultipleViewItem, datasetsFilter: "", historiesFilter: "" };
    },
    methods: {
        onViewCollection(collection) {},
        updateFilter(filter) {},
    },
};
</script>

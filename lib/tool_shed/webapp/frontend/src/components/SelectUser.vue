<script setup lang="ts">
import { computed, ref, watch } from "vue"
import { useUsersStore } from "@/stores"
import { storeToRefs } from "pinia"

interface SelectUserProps {
    label?: string
    persistSelection?: boolean
    dense?: boolean
}

const props = withDefaults(defineProps<SelectUserProps>(), {
    label: "Select user to add",
    persistSelection: false,
    dense: true,
})

const usersStore = useUsersStore()
void usersStore.getAll()

const { users } = storeToRefs(usersStore)

const allOptions = computed(() => users?.value.map((u) => u.username))
const options = ref(allOptions.value)
const selected = ref(null)

const emit = defineEmits(["selectedUser"])

watch(selected, (user) => {
    if (user) {
        emit("selectedUser", user)
    }
    if (!props.persistSelection) {
        selected.value = null
    }
})

function filterFn(val: string, update: (cbFn: () => void) => void) {
    update(() => {
        const needle = val.toLocaleLowerCase()
        if (needle == "") {
            options.value = allOptions.value
        }
        options.value = options.value.filter((v) => v.toLocaleLowerCase().indexOf(needle) > -1)
    })
}

const hideSelected = computed(() => !props.persistSelection)
</script>
<template>
    <q-select
        :dense="dense"
        filled
        use-input
        :hide-selected="hideSelected"
        :label="label"
        v-model="selected"
        input-debounce="0"
        @filter="filterFn"
        :options="options"
    />
</template>

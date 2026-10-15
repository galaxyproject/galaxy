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

const needle = ref("")
// Users can arrive after the menu opens, so filter the store's current list.
const options = computed(() =>
    users.value.map((u) => u.username).filter((v) => v.toLocaleLowerCase().indexOf(needle.value) > -1),
)
const selected = ref(null)

const emit = defineEmits(["selectedUser", "cleared"])

watch(selected, (user) => {
    if (user) {
        emit("selectedUser", user)
    } else if (props.persistSelection) {
        emit("cleared")
    }
    if (!props.persistSelection) {
        selected.value = null
    }
})

function filterFn(val: string, update: (cbFn: () => void) => void) {
    update(() => {
        needle.value = val.toLocaleLowerCase()
    })
}

const hideSelected = computed(() => !props.persistSelection)
</script>
<template>
    <q-select
        :dense="dense"
        filled
        use-input
        clearable
        :hide-selected="hideSelected"
        :label="label"
        v-model="selected"
        input-debounce="0"
        @filter="filterFn"
        @keyup.delete="selected = null"
        :options="options"
    />
</template>

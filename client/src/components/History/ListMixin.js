export default {
    data() {
        return {
            listState: {
                showSelection: false,
                selected: new Map(),
                expanded: new Set(),
            },
        };
    },

    methods: {
        isSelected(item) {
            const { type_id } = item;
            return this.listState.selected.has(type_id);
        },
        setSelected(item, bSelected) {
            const { type_id } = item;
            const newSelected = new Map(this.listState.selected);
            bSelected ? newSelected.set(type_id, item) : newSelected.delete(type_id);
            this.listState.selected = newSelected;
        },
        selectItems(items = []) {
            const newItems = [...this.listState.selected.values(), ...items];
            const newEntries = newItems.map((item) => [item.type_id, item]);
            this.listState.selected = new Map(newEntries);
        },
        unselectItems(items = []) {
            const doomedKeys = items.map((item) => item.type_id);
            const existing = this.listState.selected.entries();
            const newEntries = Array.from(existing).filter(([key]) => {
                return !doomedKeys.includes(key);
            });
            this.listState.selected = new Map(newEntries);
        },
        isExpanded({ type_id }) {
            return this.listState.expanded.has(type_id);
        },
        setExpanded({ type_id }, val) {
            const newSet = new Set(this.listState.expanded);
            val ? newSet.add(type_id) : newSet.delete(type_id);
            this.listState.expanded = newSet;
        },
        resetSelection() {
            this.listState.selected = new Map();
        },
        resetExpanded() {
            this.listState.expanded = new Set();
        },
    },

    provide() {
        return {
            listState: this.listState,
            isSelected: this.isSelected,
            setSelected: this.setSelected,
            select: this.select,
            unselect: this.unselect,
            isExpanded: this.isExpanded,
            setExpanded: this.setExpanded,
            resetSelection: this.resetSelection,
            resetExpanded: this.resetExpanded,
        };
    },

    watch: {
        "listState.selected": function (newSet) {
            if (newSet.size > 0) {
                this.showSelection = true;
            }
        },
    },
};

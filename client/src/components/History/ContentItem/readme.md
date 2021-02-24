The components in this folder represent the elements of the history. The components in this folder
[use the dynamic component syntax](https://vuejs.org/v2/guide/components.html#Dynamic-Components) to
change their type definition based on the data provided in the "item" property.

```html static
<!-- from HistoryContentItem.vue -->
<template>
    <component
        :is="contentItemComponent"
        class="content-item p-1"
        v-on="$listeners"
        ...
    />
</template>
```

A HistoryContentItem either be a loose dataset at the top of the history or a dataset collection
which can be drilled-down into.

CollectionContentItems are nested elements, and are primarily read-only because they live inside of
a collection. They are similarly split between nested datasets and nested dataset collections which
can be further drilled down into.

Initially attempts were made to consolidate the 2 kinds of datasets and the 2 kins of collections,
but there were enough differences that it was no longer convenient to attempt to if/then all the
conditional functionality. So there's 4 components now.


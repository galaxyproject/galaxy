<script>
import CollectionCreator from "./CollectionCreator";
export default {
    components: {
        CollectionCreator,
    },
    methods: {
        _setUpCommonSettings: function (attributes) {
            this.hideOriginals = attributes.defaultHideSourceItems || false;
        },
    },
};
</script>

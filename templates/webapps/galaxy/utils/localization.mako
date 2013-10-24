<%def name="localize_js_strings( strings_to_localize )">
##PRECONDITION: static/scripts/utils/localization.js should be loaded first
## adds localized versions of strings to the JS GalaxyLocalization for use in later JS
##  where strings_to_localize is a list of strings to localize
<script type="text/javascript">
    ## strings need to be mako rendered in order to use the '_' gettext helper for localization
    ##  these are then cached in the js object
    GalaxyLocalization.setLocalizedString(
        ${ h.to_json_string( dict([ ( string, _(string) ) for string in strings_to_localize ]) ) }
    );
</script>
</%def>

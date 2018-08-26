define(["i18n!nls/locale"],function(e){e.hasOwnProperty("__root")&&(locale=sessionStorage.getItem("currentLocale"),locale&&(e=e["__"+locale]||e["__"+locale.split("-")[0]]||e.__root));var o=function(o){return e[o]||o};return o.cacheNonLocalized=!1,o});
//# sourceMappingURL=../../maps/utils/localization.js.map

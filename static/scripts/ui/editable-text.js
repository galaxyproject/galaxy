!function(a){"function"==typeof define&&define.amd?define(["jquery"],a):a(jQuery)}(function(a){"use_strict";var b=a;b.fn.make_text_editable=function(a){var c="num_cols"in a?a.num_cols:30,d="num_rows"in a?a.num_rows:4,e="use_textarea"in a&&a.use_textarea,f="on_finish"in a?a.on_finish:null,g="help_text"in a?a.help_text:null,h=b(this);return h.addClass("editable-text").click(function(g){if(!(b(this).children(":input").length>0)){h.removeClass("editable-text");var i,j,k=function(a){h.find(":input").remove(),""!==a?h.text(a):h.html("<br>"),h.addClass("editable-text"),f&&f(a)},l="cur_text"in a?a.cur_text:h.text();e?(i=b("<textarea/>").attr({rows:d,cols:c}).text(b.trim(l)).keyup(function(a){27===a.keyCode&&k(l)}),j=b("<button/>").text("Done").click(function(){return k(i.val()),!1})):i=b("<input type='text'/>").attr({value:b.trim(l),size:c}).blur(function(){k(l)}).keyup(function(a){27===a.keyCode?b(this).trigger("blur"):13===a.keyCode&&k(b(this).val()),a.stopPropagation()}),h.text(""),h.append(i),j&&h.append(j),i.focus(),i.select(),g.stopPropagation()}}),g&&h.attr("title",g).tooltip(),h}});
//# sourceMappingURL=../../maps/ui/editable-text.js.map
define(["utils/utils"],function(){return Backbone.Model.extend({initialize:function(a){this.app=a},checksum:function(){var a="",b=this;return this.app.section.$el.find(".section-row").each(function(){var c=$(this).attr("id"),d=b.app.field_list[c];d&&(a+=c+":"+JSON.stringify(d.value&&d.value())+";")}),a},create:function(){function a(a,b,d){c.map_dict[a]=b,e[a]=d}function b(d,e){for(var f in e){var g=e[f];if(g.input){var h=g.input,i=d;switch(""!=d&&(i+="|"),i+=h.name,h.type){case"repeat":var j="section-",k=[],l=null;for(var m in g){var n=m.indexOf(j);-1!=n&&(n+=j.length,k.push(parseInt(m.substr(n))),l||(l=m.substr(0,n)))}k.sort(function(a,b){return a-b});var f=0;for(var o in k)b(i+"_"+f++,g[l+k[o]]);break;case"conditional":var p=c.app.field_list[h.id].value();a(i+"|"+h.test_param.name,h.id,p);var q=c.matchCase(h,p);-1!=q&&b(i,e[h.id+"-section-"+q]);break;case"section":b(!h.flat&&i||"",g);break;default:var r=c.app.field_list[h.id];if(r&&r.value){var p=r.value();if((void 0===h.ignore||h.ignore!=p)&&(a(i,h.id,p),h.payload))for(var s in h.payload)a(s,h.id,h.payload[s])}}}}}var c=this,d={};this._iterate(this.app.section.$el,d);var e={};return this.map_dict={},b("",d),e},match:function(a){return this.map_dict&&this.map_dict[a]},matchCase:function(a,b){"boolean"==a.test_param.type&&(b="true"==b?a.test_param.truevalue||"true":a.test_param.falsevalue||"false");for(var c in a.cases)if(a.cases[c].value==b)return c;return-1},matchModel:function(a,b){function c(a,d){for(var f in d){var g=d[f],h=g.name;switch(""!=a&&(h=a+"|"+h),g.type){case"repeat":for(var i in g.cache)c(h+"_"+i,g.cache[i]);break;case"conditional":var j=g.test_param&&g.test_param.value,k=e.matchCase(g,j);-1!=k&&c(h,g.cases[k].inputs);break;case"section":c(h,g.inputs);break;default:var l=e.map_dict[h];l&&b(l,g)}}}var d={},e=this;return c("",a.inputs),d},matchResponse:function(a){function b(a,e){if("string"==typeof e){var f=d.map_dict[a];f&&(c[f]=e)}else for(var g in e){var h=g;if(""!==a){var i="|";e instanceof Array&&(i="_"),h=a+i+h}b(h,e[g])}}var c={},d=this;return b("",a),c},_iterate:function(a,b){var c=this,d=$(a).children();d.each(function(){var a=this,d=$(a).attr("id");if($(a).hasClass("section-row")){b[d]={};var e=c.app.input_list[d];e&&(b[d]={input:e}),c._iterate(a,b[d])}else c._iterate(a,b)})}})});
//# sourceMappingURL=../../../maps/mvc/form/form-data.js.map
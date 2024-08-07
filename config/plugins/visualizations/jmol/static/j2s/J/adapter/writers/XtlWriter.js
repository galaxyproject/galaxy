Clazz.declarePackage("J.adapter.writers");
Clazz.load(null, "J.adapter.writers.XtlWriter", ["JU.PT"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.haveUnitCell = true;
this.isHighPrecision = true;
this.slop = 0;
this.precision = 0;
Clazz.instantialize(this, arguments);}, J.adapter.writers, "XtlWriter", null);
Clazz.defineMethod(c$, "clean", 
function(d){
if (!this.isHighPrecision) return this.cleanF(d);
var t;
return (!this.haveUnitCell || (t = J.adapter.writers.XtlWriter.twelfthsOf(d)) < 0 ? JU.PT.formatF(d, 18, 12, false, false) : (d < 0 ? "   -" : "    ") + J.adapter.writers.XtlWriter.twelfths[t]);
}, "~N");
c$.twelfthsOf = Clazz.defineMethod(c$, "twelfthsOf", 
function(f){
if (f == 0) return 0;
f = Math.abs(f * 12);
var i = Math.round(f);
return (i <= 12 && Math.abs(f - i) < J.adapter.writers.XtlWriter.SLOPD * 12 ? i : -1);
}, "~N");
Clazz.defineMethod(c$, "cleanF", 
function(f){
var t;
if (this.slop != 0) return this.cleanSlop(f);
return (!this.haveUnitCell || (t = J.adapter.writers.XtlWriter.twelfthsOfF(f)) < 0 ? JU.PT.formatF(f, 12, 7, false, false) : (f < 0 ? "   -" : "    ") + J.adapter.writers.XtlWriter.twelfthsF[t]);
}, "~N");
Clazz.defineMethod(c$, "cleanSlop", 
function(f){
return JU.PT.formatF(f, this.precision + 6, this.precision, false, false);
}, "~N");
c$.twelfthsOfF = Clazz.defineMethod(c$, "twelfthsOfF", 
function(f){
if (f == 0) return 0;
f = Math.abs(f * 12);
var i = Math.round(f);
return (i <= 12 && Math.abs(f - i) < J.adapter.writers.XtlWriter.SLOPF * 12 ? i : -1);
}, "~N");
Clazz.defineMethod(c$, "cleanT", 
function(d){
var s = this.clean(d);
if (this.isHighPrecision) return s;
var i = s.length;
while (--i >= 2 && s.charAt(i) == '0' && s.charAt(i - 1) != '.') {
}
return s.substring(0, i + 1);
}, "~N");
c$.SLOPD = 0.000000000010;
c$.SLOPF = 0.0000010;
c$.twelfths =  Clazz.newArray(-1, ["0.000000000000", "0.083333333333", "0.166666666667", "0.250000000000", "0.333333333333", "0.416666666667", "0.500000000000", "0.583333333333", "0.666666666667", "0.750000000000", "0.833333333333", "0.916666666667", "1.000000000000"]);
c$.twelfthsF =  Clazz.newArray(-1, ["0.0000000", "0.0833333", "0.1666667", "0.2500000", "0.3333333", "0.4166667", "0.5000000", "0.5833333", "0.6666667", "0.7500000", "0.8333333", "0.9166667", "1.0000000"]);
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024

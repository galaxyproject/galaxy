Clazz.declarePackage("JS");
Clazz.load(["java.util.Hashtable"], "JS.SpaceGroup", ["java.util.Arrays", "JU.AU", "$.Lst", "$.M4", "$.P3", "$.PT", "$.SB", "JS.HallInfo", "$.HallTranslation", "$.SymmetryOperation", "$.UnitCell", "JU.Logger"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.operations = null;
this.finalOperations = null;
this.allOperations = null;
this.xyzList = null;
this.uniqueAxis = '\0';
this.axisChoice = '\0';
this.itaNumber = null;
this.jmolId = null;
this.clegId = null;
this.operationCount = 0;
this.latticeOp = -1;
this.isBio = false;
this.latticeType = 'P';
this.itaTransform = null;
this.itaIndex = null;
this.index = 0;
this.derivedIndex = -1;
this.isSSG = false;
this.name = "unknown!";
this.hallSymbol = null;
this.hallSymbolAlt = null;
this.crystalClass = null;
this.hmSymbol = null;
this.jmolIdExt = null;
this.hallInfo = null;
this.latticeParameter = 0;
this.modDim = 0;
this.doNormalize = true;
this.info = null;
this.nHallOperators = null;
this.hmSymbolFull = null;
this.hmSymbolExt = null;
this.hmSymbolAbbr = null;
this.hmSymbolAlternative = null;
this.hmSymbolAbbrShort = null;
this.ambiguityType = '\0';
this.strName = null;
this.displayName = null;
Clazz.instantialize(this, arguments);}, JS, "SpaceGroup", null, Cloneable);
Clazz.makeConstructor(c$, 
function(index, strData, doInit){
++JS.SpaceGroup.sgIndex;
if (index < 0) index = JS.SpaceGroup.sgIndex;
this.index = index;
this.init(doInit && strData == null);
if (doInit && strData != null) this.buildSelf(strData);
}, "~N,~S,~B");
Clazz.defineMethod(c$, "setFrom", 
function(sg, isITA){
if (isITA) {
this.setName(sg.itaNumber.equals("0") ? this.clegId : "HM:" + sg.hmSymbolFull + " #" + this.clegId);
this.derivedIndex = -2;
} else {
this.setName(sg.getName());
this.derivedIndex = sg.index;
}this.clegId = sg.clegId;
this.itaIndex = sg.itaIndex;
this.crystalClass = sg.crystalClass;
this.hallSymbol = sg.hallSymbol;
this.hmSymbol = sg.hmSymbol;
this.hmSymbolAbbr = sg.hmSymbolAbbr;
this.hmSymbolAbbrShort = sg.hmSymbolAbbrShort;
this.hmSymbolAlternative = sg.hmSymbolAlternative;
this.hmSymbolExt = sg.hmSymbolExt;
this.hmSymbolFull = sg.hmSymbolFull;
this.itaNumber = sg.itaNumber;
this.itaTransform = sg.itaTransform;
this.jmolId = null;
this.jmolIdExt = null;
this.latticeType = sg.latticeType;
this.strName = this.displayName = null;
return this;
}, "JS.SpaceGroup,~B");
c$.getNull = Clazz.defineMethod(c$, "getNull", 
function(doInit, doNormalize, doFinalize){
var sg =  new JS.SpaceGroup(-1, null, doInit);
sg.doNormalize = doNormalize;
if (doFinalize) sg.setFinalOperations();
return sg;
}, "~B,~B,~B");
Clazz.defineMethod(c$, "init", 
function(addXYZ){
this.xyzList =  new java.util.Hashtable();
this.operationCount = 0;
if (addXYZ) this.addSymmetry("x,y,z", 0, false);
}, "~B");
c$.createSpaceGroup = Clazz.defineMethod(c$, "createSpaceGroup", 
function(desiredSpaceGroupIndex, name, data, modDim){
var sg = null;
if (desiredSpaceGroupIndex >= 0) {
sg = JS.SpaceGroup.SG[desiredSpaceGroupIndex];
} else {
if (Clazz.instanceOf(data,"JU.Lst")) sg = JS.SpaceGroup.createSGFromList(name, data);
 else sg = JS.SpaceGroup.determineSpaceGroupNA(name, data);
if (sg == null) sg = JS.SpaceGroup.createSpaceGroupN(modDim <= 0 ? name : "x1,x2,x3,x4,x5,x6,x7,x8,x9".substring(0, modDim * 3 + 8));
}if (sg != null) sg.generateAllOperators(null);
return sg;
}, "~N,~S,~O,~N");
Clazz.defineMethod(c$, "cloneInfoTo", 
function(sg0){
try {
var sg = this.clone();
sg.operations = sg0.operations;
sg.finalOperations = sg0.finalOperations;
sg.xyzList = sg0.xyzList;
return sg;
} catch (e) {
if (Clazz.exceptionOf(e,"CloneNotSupportedException")){
return null;
} else {
throw e;
}
}
}, "JS.SpaceGroup");
Clazz.defineMethod(c$, "getItaIndex", 
function(){
return (this.itaIndex != null && !"--".equals(this.itaIndex) ? this.itaIndex : !"0".equals(this.itaNumber) ? this.itaNumber : !"--".equals(this.hallSymbol) ? "[" + this.hallSymbol + "]" : "?");
});
Clazz.defineMethod(c$, "getIndex", 
function(){
return (this.derivedIndex >= 0 ? this.derivedIndex : this.index);
});
c$.createSGFromList = Clazz.defineMethod(c$, "createSGFromList", 
function(name, data){
var sg =  new JS.SpaceGroup(-1, "0;--;--;0;--;--;--", true);
sg.doNormalize = false;
sg.setName(name);
var n = data.size();
for (var i = 0; i < n; i++) {
var operation = data.get(i);
if (Clazz.instanceOf(operation,"JS.SymmetryOperation")) {
var op = operation;
var iop = sg.addOp(op, op.xyz, false);
sg.operations[iop].setTimeReversal(op.timeReversal);
} else {
sg.addSymmetrySM("xyz matrix:" + operation, operation);
}}
var sgn = sg.getDerivedSpaceGroup();
if (sgn != null) sg = sgn;
return sg;
}, "~S,JU.Lst");
Clazz.defineMethod(c$, "addSymmetry", 
function(xyz, opId, allowScaling){
xyz = xyz.toLowerCase();
return (xyz.indexOf("[[") < 0 && xyz.indexOf("x4") < 0 && xyz.indexOf(";") < 0 && (xyz.indexOf("x") < 0 || xyz.indexOf("y") < 0 || xyz.indexOf("z") < 0) ? -1 : this.addOperation(xyz, opId, allowScaling));
}, "~S,~N,~B");
Clazz.defineMethod(c$, "setFinalOperations", 
function(){
this.setFinalOperationsForAtoms(3, null, 0, 0, false);
});
Clazz.defineMethod(c$, "setFinalOperationsForAtoms", 
function(dim, atoms, atomIndex, count, doNormalize){
if (this.hallInfo == null && this.latticeParameter != 0) {
var h =  new JS.HallInfo(JS.HallTranslation.getHallLatticeEquivalent(this.latticeParameter));
this.generateAllOperators(h);
}this.finalOperations = null;
this.isBio = (this.name.indexOf("bio") >= 0);
if (!this.isBio && this.index >= JS.SpaceGroup.SG.length && this.name.indexOf("SSG:") < 0 && this.name.indexOf("[subsystem") < 0) {
var sg = this.getDerivedSpaceGroup();
if (sg != null && sg !== this) {
this.setFrom(sg, false);
}}if (this.operationCount == 0) this.addOperation("x,y,z", 1, false);
this.finalOperations =  new Array(this.operationCount);
var op = null;
var doOffset = (doNormalize && count > 0 && atoms != null);
if (doOffset) {
op = this.finalOperations[0] =  new JS.SymmetryOperation(this.operations[0], 0, true);
if (op.sigma == null) JS.SymmetryOperation.normalizeOperationToCentroid(dim, op, atoms, atomIndex, count);
var atom = atoms[atomIndex];
var c = JU.P3.newP(atom);
op.rotTrans(c);
if (c.distance(atom) > 0.0001) {
for (var i = 0; i < count; i++) {
atom = atoms[atomIndex + i];
c.setT(atom);
op.rotTrans(c);
atom.setT(c);
}
}if (!doNormalize) op = null;
}for (var i = 0; i < this.operationCount; i++) {
if (i > 0 || op == null) {
op = this.finalOperations[i] =  new JS.SymmetryOperation(this.operations[i], 0, doNormalize);
}if (doOffset && op.sigma == null) {
JS.SymmetryOperation.normalizeOperationToCentroid(dim, op, atoms, atomIndex, count);
}op.getCentering();
}
}, "~N,~A,~N,~N,~B");
Clazz.defineMethod(c$, "getOperationCount", 
function(){
if (this.finalOperations == null) this.setFinalOperations();
return this.finalOperations.length;
});
Clazz.defineMethod(c$, "getOperation", 
function(i){
return this.finalOperations[i];
}, "~N");
Clazz.defineMethod(c$, "getAdditionalOperationsCount", 
function(){
if (this.finalOperations == null) this.setFinalOperations();
if (this.allOperations == null) {
this.allOperations = JS.SymmetryOperation.getAdditionalOperations(this.finalOperations);
}return this.allOperations.length - this.getOperationCount();
});
Clazz.defineMethod(c$, "getAdditionalOperations", 
function(){
this.getAdditionalOperationsCount();
return this.allOperations;
});
Clazz.defineMethod(c$, "getAllOperation", 
function(i){
return this.allOperations[i];
}, "~N");
Clazz.defineMethod(c$, "getXyz", 
function(i, doNormalize){
return (this.finalOperations == null ? this.operations[i].getXyz(doNormalize) : this.finalOperations[i].getXyz(doNormalize));
}, "~N,~B");
c$.findSpaceGroupFromXYZ = Clazz.defineMethod(c$, "findSpaceGroupFromXYZ", 
function(xyzList){
var sg =  new JS.SpaceGroup(-1, "0;--;--;0;--;--;--", true);
sg.doNormalize = false;
var xyzlist = xyzList.$plit(";");
for (var i = 0, n = xyzlist.length; i < n; i++) {
var op =  new JS.SymmetryOperation(null, i, false);
op.setMatrixFromXYZ(xyzlist[i], 0, false);
sg.addOp(op, xyzlist[i], false);
}
return JS.SpaceGroup.findSpaceGroup(sg.operationCount, sg.getCanonicalSeitzList());
}, "~S");
c$.getInfo = Clazz.defineMethod(c$, "getInfo", 
function(sg, spaceGroup, params, asMap, andNonstandard){
try {
if (sg != null && sg.index >= JS.SpaceGroup.SG.length) {
var sgDerived = JS.SpaceGroup.findSpaceGroup(sg.operationCount, sg.getCanonicalSeitzList());
if (sgDerived != null) sg = sgDerived;
}if (params != null) {
if (sg == null) {
if (spaceGroup.indexOf("[") >= 0) spaceGroup = spaceGroup.substring(0, spaceGroup.indexOf("[")).trim();
if (spaceGroup.equals("unspecified!")) return "no space group identified in file";
sg = JS.SpaceGroup.determineSpaceGroupNA(spaceGroup, params);
}} else if (spaceGroup.equalsIgnoreCase("ALL")) {
return JS.SpaceGroup.dumpAll(asMap);
} else if (spaceGroup.equalsIgnoreCase("MAP")) {
return JS.SpaceGroup.dumpAll(true);
} else if (spaceGroup.equalsIgnoreCase("ALLSEITZ")) {
return JS.SpaceGroup.dumpAllSeitz();
} else {
sg = JS.SpaceGroup.determineSpaceGroupN(spaceGroup);
}if (sg == null) {
var sgFound = JS.SpaceGroup.createSpaceGroupN(spaceGroup);
if (sgFound != null) sgFound = JS.SpaceGroup.findSpaceGroup(sgFound.operationCount, sgFound.getCanonicalSeitzList());
if (sgFound != null) sg = sgFound;
}if (sg != null) {
if (asMap) {
return sg.dumpInfoObj();
}var sb =  new JU.SB();
while (sg != null) {
sb.append(sg.dumpInfo());
if (sg.index >= JS.SpaceGroup.SG.length || !andNonstandard) break;
sg = JS.SpaceGroup.determineSpaceGroupNS(spaceGroup, sg);
}
return sb.toString();
}return asMap ? null : "?";
} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
return "?";
} else {
throw e;
}
}
}, "JS.SpaceGroup,~S,~A,~B,~B");
Clazz.defineMethod(c$, "dumpInfo", 
function(){
var info = this.dumpCanonicalSeitzList();
if (Clazz.instanceOf(info,"JS.SpaceGroup")) return (info).dumpInfo();
var sb =  new JU.SB().append("\nHermann-Mauguin symbol: ");
if (this.hmSymbol == null || this.hmSymbolExt == null) sb.append("?");
 else sb.append(this.hmSymbol).append(this.hmSymbolExt.length > 0 ? ":" + this.hmSymbolExt : "");
if (this.itaNumber != null) {
sb.append("\ninternational table number: ").append(this.itaNumber).append(this.itaTransform != null ? ":" + this.itaTransform : "").append("\ncrystal class: " + this.crystalClass);
}if (this.jmolId != null) {
sb.append("\nJmol_ID: ").append(this.jmolId).append(" (" + this.itaIndex + ")");
}sb.append("\n\n").append(this.hallInfo == null ? "Hall symbol unknown" : JU.Logger.debugging ? this.hallInfo.dumpInfo() : "");
sb.append("\n\n").appendI(this.operationCount).append(" operators").append(this.hallInfo != null && !this.hallInfo.hallSymbol.equals("--") ? " from Hall symbol " + this.hallInfo.hallSymbol + "  #" + this.jmolId : "").append(": ");
for (var i = 0; i < this.operationCount; i++) {
sb.append("\n").append(this.operations[i].xyz);
}
return sb.toString();
});
Clazz.defineMethod(c$, "dumpInfoObj", 
function(){
var info = this.dumpCanonicalSeitzList();
if (Clazz.instanceOf(info,"JS.SpaceGroup")) return (info).dumpInfoObj();
var map =  new java.util.Hashtable();
if (this.itaNumber != null && !this.itaNumber.equals("0")) {
var s = (this.hmSymbol == null || this.hmSymbolExt == null ? "?" : this.hmSymbol + (this.hmSymbolExt.length > 0 ? ":" + this.hmSymbolExt : ""));
map.put("HermannMauguinSymbol", s);
map.put("ita", Integer.$valueOf(JU.PT.parseInt(this.itaNumber)));
map.put("itaIndex", this.itaIndex == null ? "n/a" : this.itaIndex);
map.put("clegId", this.itaIndex == null ? "n/a" : this.clegId);
if (this.jmolId != null) map.put("jmolId", this.jmolId);
map.put("crystalClass", this.crystalClass);
map.put("operationCount", Integer.$valueOf(this.operationCount));
}var lst =  new JU.Lst();
for (var i = 0; i < this.operationCount; i++) {
lst.addLast(this.operations[i].xyz);
}
map.put("operationsXYZ", lst);
if (this.hallInfo != null && this.hallInfo.hallSymbol != null) map.put("HallSymbol", this.hallInfo.hallSymbol);
if (this.hallSymbolAlt != null) map.put("HallSymbolAlt", this.hallSymbolAlt);
return map;
});
Clazz.defineMethod(c$, "getName", 
function(){
return this.name;
});
Clazz.defineMethod(c$, "getLatticeDesignation", 
function(){
return JS.HallTranslation.getLatticeDesignation(this.latticeParameter);
});
Clazz.defineMethod(c$, "setLatticeParam", 
function(latticeParameter){
this.latticeParameter = latticeParameter;
if (latticeParameter > 10) this.latticeParameter = -JS.HallTranslation.getLatticeIndex(JS.HallTranslation.getLatticeCode(latticeParameter));
}, "~N");
Clazz.defineMethod(c$, "dumpCanonicalSeitzList", 
function(){
if (this.nHallOperators != null) {
this.hallInfo =  new JS.HallInfo(this.hallSymbol);
this.generateAllOperators(null);
}var s = this.getCanonicalSeitzList();
if (this.index >= JS.SpaceGroup.SG.length) {
var sgDerived = JS.SpaceGroup.findSpaceGroup(this.operationCount, s);
if (sgDerived != null) return sgDerived.getCanonicalSeitzList();
}return (this.index >= 0 && this.index < JS.SpaceGroup.SG.length ? this.hallSymbol + " = " : "") + s;
});
Clazz.defineMethod(c$, "getDerivedSpaceGroup", 
function(){
if (this.derivedIndex == -2 || this.index >= 0 && this.index < JS.SpaceGroup.SG.length || this.modDim > 0 || this.operations == null || this.operations.length == 0 || this.operations[0].timeReversal != 0) return this;
if (this.finalOperations != null) this.setFinalOperations();
var s = this.getCanonicalSeitzList();
return (s == null ? null : JS.SpaceGroup.findSpaceGroup(this.operationCount, s));
});
Clazz.defineMethod(c$, "getCanonicalSeitzList", 
function(){
return JS.SpaceGroup.getCanonicalSeitzForOperations(this.operations, this.operationCount);
});
c$.getCanonicalSeitzForOperations = Clazz.defineMethod(c$, "getCanonicalSeitzForOperations", 
function(operations, n){
var list =  new Array(n);
for (var i = 0; i < n; i++) list[i] = JS.SymmetryOperation.dumpSeitz(operations[i], true);

java.util.Arrays.sort(list, 0, n);
var sb =  new JU.SB().append("\n[");
for (var i = 0; i < n; i++) sb.append(list[i].$replace('\t', ' ').$replace('\n', ' ')).append("; ");

sb.append("]");
return sb.toString();
}, "~A,~N");
c$.findSpaceGroup = Clazz.defineMethod(c$, "findSpaceGroup", 
function(opCount, s){
var lst = JS.SpaceGroup.htByOpCount.get(Integer.$valueOf(opCount));
if (lst != null) for (var i = 0, n = lst.size(); i < n; i++) {
var sg = lst.get(i);
if (JS.SpaceGroup.getCanonicalSeitz(sg.index).indexOf(s) >= 0) return JS.SpaceGroup.SG[sg.index];
}
return null;
}, "~N,~S");
c$.dumpAll = Clazz.defineMethod(c$, "dumpAll", 
function(asMap){
if (asMap) {
var info =  new JU.Lst();
for (var i = 0; i < JS.SpaceGroup.SG.length; i++) info.addLast(JS.SpaceGroup.SG[i].dumpInfoObj());

return info;
}var sb =  new JU.SB();
for (var i = 0; i < JS.SpaceGroup.SG.length; i++) sb.append("\n----------------------\n" + JS.SpaceGroup.SG[i].dumpInfo());

return sb.toString();
}, "~B");
c$.dumpAllSeitz = Clazz.defineMethod(c$, "dumpAllSeitz", 
function(){
var sb =  new JU.SB();
for (var i = 0; i < JS.SpaceGroup.SG.length; i++) sb.append("\n").appendO(JS.SpaceGroup.getCanonicalSeitz(i));

return sb.toString();
});
c$.getCanonicalSeitz = Clazz.defineMethod(c$, "getCanonicalSeitz", 
function(i){
if (JS.SpaceGroup.canonicalSeitzList == null) JS.SpaceGroup.canonicalSeitzList =  new Array(JS.SpaceGroup.SG.length);
var cs = JS.SpaceGroup.canonicalSeitzList[i];
return (cs == null ? JS.SpaceGroup.canonicalSeitzList[i] = JS.SpaceGroup.SG[i].dumpCanonicalSeitzList().toString() : cs);
}, "~N");
Clazz.defineMethod(c$, "setLattice", 
function(latticeCode, isCentrosymmetric){
this.latticeParameter = JS.HallTranslation.getLatticeIndex(latticeCode);
if (!isCentrosymmetric) this.latticeParameter = -this.latticeParameter;
}, "~S,~B");
c$.createSpaceGroupN = Clazz.defineMethod(c$, "createSpaceGroupN", 
function(name){
name = name.trim();
var sg = JS.SpaceGroup.determineSpaceGroupN(name);
var hallInfo;
if (sg == null) {
hallInfo =  new JS.HallInfo(name);
if (hallInfo.nRotations > 0) {
sg =  new JS.SpaceGroup(-1, "0;--;--;0;--;--;" + name, true);
sg.hallInfo = hallInfo;
sg.hallSymbol = hallInfo.hallSymbol;
sg.setName("[" + sg.hallSymbol + "]");
sg.jmolId = null;
} else if (name.indexOf(",") >= 0) {
sg =  new JS.SpaceGroup(-1, "0;--;--;0;--;--;--", true);
sg.doNormalize = false;
sg.generateOperatorsFromXyzInfo(name);
}}if (sg != null) sg.generateAllOperators(null);
return sg;
}, "~S");
Clazz.defineMethod(c$, "addOperation", 
function(xyz0, opId, allowScaling){
if (xyz0 == null || xyz0.length < 3) {
this.init(false);
return -1;
}xyz0 = JU.PT.rep(xyz0, " ", "");
var isSpecial = (xyz0.charAt(0) == '=');
if (isSpecial) xyz0 = xyz0.substring(1);
var id = this.checkXYZlist(xyz0);
if (id >= 0) return id;
if (xyz0.startsWith("x1,x2,x3,x4") && this.modDim == 0) {
this.xyzList.clear();
this.operationCount = 0;
this.modDim = JU.PT.parseInt(xyz0.substring(xyz0.lastIndexOf("x") + 1)) - 3;
} else if (xyz0.indexOf("m") >= 0) {
xyz0 = JU.PT.rep(xyz0, "+m", "m");
if (xyz0.equals("x,y,z,m") || xyz0.equals("x,y,z(mx,my,mz)")) {
this.xyzList.clear();
this.operationCount = 0;
}}var op =  new JS.SymmetryOperation(null, opId, this.doNormalize);
if (!op.setMatrixFromXYZ(xyz0, this.modDim, allowScaling)) {
JU.Logger.error("couldn't interpret symmetry operation: " + xyz0);
return -1;
}if (xyz0.charAt(0) == '!') {
xyz0 = xyz0.substring(xyz0.lastIndexOf('!') + 1);
}return this.addOp(op, xyz0, isSpecial);
}, "~S,~N,~B");
Clazz.defineMethod(c$, "checkXYZlist", 
function(xyz){
return (this.xyzList.containsKey(xyz) ? this.xyzList.get(xyz).intValue() : -1);
}, "~S");
Clazz.defineMethod(c$, "addOp", 
function(op, xyz0, isSpecial){
var xyz = op.xyz;
if (!isSpecial) {
var id = this.checkXYZlist(xyz);
if (id >= 0) return id;
if (this.latticeOp < 0) {
var xxx = JU.PT.replaceAllCharacters(this.modDim > 0 ? JS.SymmetryOperation.replaceXn(xyz, this.modDim + 3) : xyz, "+123/", "");
if (this.xyzList.containsKey(xxx + "!")) {
this.latticeOp = this.operationCount;
} else {
this.xyzList.put(xxx + "!", Integer.$valueOf(this.operationCount));
}}this.xyzList.put(xyz, Integer.$valueOf(this.operationCount));
}if (!xyz.equals(xyz0)) this.xyzList.put(xyz0, Integer.$valueOf(this.operationCount));
if (this.operations == null) this.operations =  new Array(4);
if (this.operationCount == this.operations.length) this.operations = JU.AU.arrayCopyObject(this.operations, this.operationCount * 2);
this.operations[this.operationCount++] = op;
op.number = this.operationCount;
if (op.timeReversal != 0) this.operations[0].timeReversal = 1;
if (JU.Logger.debugging) JU.Logger.debug("\naddOperation " + this.operationCount + op.dumpInfo());
return this.operationCount - 1;
}, "JS.SymmetryOperation,~S,~B");
Clazz.defineMethod(c$, "generateOperatorsFromXyzInfo", 
function(xyzInfo){
this.init(true);
var terms = JU.PT.split(xyzInfo.toLowerCase(), ";");
for (var i = 0; i < terms.length; i++) this.addSymmetry(terms[i], 0, false);

}, "~S");
Clazz.defineMethod(c$, "generateAllOperators", 
function(h){
if (h == null) {
if (this.operationCount > 0) return;
if (this.hallSymbol.endsWith("?")) {
this.checkHallOperators();
return;
}h = this.hallInfo;
this.operations =  new Array(4);
if (this.hallInfo == null || this.hallInfo.nRotations == 0) h = this.hallInfo =  new JS.HallInfo(this.hallSymbol);
this.setLattice(this.hallInfo.latticeCode, this.hallInfo.isCentrosymmetric);
this.init(true);
}switch ((h.latticeCode).charCodeAt(0)) {
case 0:
case 83:
case 84:
case 80:
this.latticeType = 'P';
break;
default:
this.latticeType = h.latticeCode;
break;
}
var mat1 =  new JU.M4();
var operation =  new JU.M4();
var newOps =  new Array(7);
for (var i = 0; i < 7; i++) newOps[i] =  new JU.M4();

for (var i = 0; i < h.nRotations; i++) {
var rt = h.rotationTerms[i];
mat1.setM4(rt.seitzMatrix12ths);
var nRot = rt.order;
newOps[0].setIdentity();
var nOps = this.operationCount;
for (var j = 1; j <= nRot; j++) {
var m = newOps[j];
m.mul2(mat1, newOps[0]);
newOps[0].setM4(m);
for (var k = 0; k < nOps; k++) {
operation.mul2(m, this.operations[k]);
operation.m03 = (Clazz.floatToInt(operation.m03) + 12) % 12;
operation.m13 = (Clazz.floatToInt(operation.m13) + 12) % 12;
operation.m23 = (Clazz.floatToInt(operation.m23) + 12) % 12;
var xyz = JS.SymmetryOperation.getXYZFromMatrix(operation, true, true, false);
if (this.checkXYZlist(xyz) >= 0) continue;
this.addSymmetrySM("!nohalf!" + xyz, operation);
}
}
}
if (this.hmSymbol == null) {
this.hmSymbol = "--";
}if (this.hmSymbol.equals("--")) {
this.hallSymbol = h.hallSymbol;
this.nHallOperators = Integer.$valueOf(this.operationCount);
}if (this.nHallOperators != null && this.operationCount != this.nHallOperators.intValue()) JU.Logger.error("Operator mismatch " + this.operationCount + " for " + this);
}, "JS.HallInfo");
Clazz.defineMethod(c$, "addSymmetrySM", 
function(xyz, operation){
var iop = this.addOperation(xyz, 0, false);
if (iop >= 0) {
var symmetryOperation = this.operations[iop];
symmetryOperation.setM4(operation);
}return iop;
}, "~S,JU.M4");
c$.determineSpaceGroupN = Clazz.defineMethod(c$, "determineSpaceGroupN", 
function(name){
return JS.SpaceGroup.determineSpaceGroup(name, 0, 0, 0, 0, 0, 0, -1);
}, "~S");
c$.determineSpaceGroupNS = Clazz.defineMethod(c$, "determineSpaceGroupNS", 
function(name, sg){
return JS.SpaceGroup.determineSpaceGroup(name, 0, 0, 0, 0, 0, 0, sg.index);
}, "~S,JS.SpaceGroup");
c$.determineSpaceGroupNA = Clazz.defineMethod(c$, "determineSpaceGroupNA", 
function(name, unitCellParams){
return (unitCellParams == null ? JS.SpaceGroup.determineSpaceGroup(name, 0, 0, 0, 0, 0, 0, -1) : JS.SpaceGroup.determineSpaceGroup(name, unitCellParams[0], unitCellParams[1], unitCellParams[2], unitCellParams[3], unitCellParams[4], unitCellParams[5], -1));
}, "~S,~A");
c$.determineSpaceGroup = Clazz.defineMethod(c$, "determineSpaceGroup", 
function(name, a, b, c, alpha, beta, gamma, lastIndex){
var i = JS.SpaceGroup.determineSpaceGroupIndex(name, a, b, c, alpha, beta, gamma, lastIndex);
return (i >= 0 ? JS.SpaceGroup.SG[i] : null);
}, "~S,~N,~N,~N,~N,~N,~N,~N");
c$.isXYZList = Clazz.defineMethod(c$, "isXYZList", 
function(name){
return (name != null && name.indexOf(",") >= 0 && name.indexOf("(") < 0 && name.indexOf(":") < 0);
}, "~S");
c$.determineSpaceGroupIndex = Clazz.defineMethod(c$, "determineSpaceGroupIndex", 
function(name, a, b, c, alpha, beta, gamma, lastIndex){
if (JS.SpaceGroup.isXYZList(name)) return -1;
if (lastIndex < 0) lastIndex = JS.SpaceGroup.SG.length;
name = name.trim().toLowerCase();
if (name.startsWith("bilbao:")) {
name = name.substring(7);
}var pt = name.indexOf("hall:");
if (pt > 0) name = name.substring(pt);
var nameType = (name.startsWith("ita/") ? 4 : name.startsWith("hall:") ? 5 : name.startsWith("hm:") ? 3 : 0);
switch (nameType) {
case 3:
case 5:
case 4:
name = name.substring(nameType);
break;
case 0:
if (name.contains("[")) {
nameType = 5;
name = name.substring(0, name.indexOf("[")).trim();
} else if (name.indexOf(".") > 0) {
nameType = 4;
}}
var nameExt = name;
var i;
var haveExtension = false;
if (nameType == 4) {
} else {
name = name.$replace('_', ' ');
if (name.length >= 2) {
i = (name.indexOf("-") == 0 ? 2 : 1);
if (i < name.length && name.charAt(i) != ' ') name = name.substring(0, i) + " " + name.substring(i);
name = JS.SpaceGroup.toCap(name, 2);
}}var ext = "";
if ((i = name.indexOf(":")) > 0) {
ext = name.substring(i + 1);
name = name.substring(0, i).trim();
haveExtension = (ext.length > 0);
}if (nameType != 4 && nameType != 5 && !haveExtension && JU.PT.isOneOf(name, JS.SpaceGroup.ambiguousHMNames)) {
ext = "?";
haveExtension = true;
}var abbr = JU.PT.replaceAllCharacters(name, " ()", "");
var s;
switch (nameType) {
case 4:
if (haveExtension) for (i = 0; i < lastIndex; i++) {
if (nameExt.equalsIgnoreCase(JS.SpaceGroup.SG[i].itaIndex)) return i;
}
 else for (i = 0; i < lastIndex; i++) {
if (name.equalsIgnoreCase(JS.SpaceGroup.SG[i].itaIndex)) return i;
}
break;
case 5:
for (i = 0; i < lastIndex; i++) {
if (JS.SpaceGroup.SG[i].hallSymbol.equalsIgnoreCase(name)) return i;
}
break;
default:
case 3:
if (nameType != 3) for (i = 0; i < lastIndex; i++) if (JS.SpaceGroup.SG[i].jmolId.equalsIgnoreCase(nameExt)) return i;

for (i = 0; i < lastIndex; i++) if (JS.SpaceGroup.SG[i].hmSymbolFull.equalsIgnoreCase(nameExt)) return i;

for (i = 0; i < lastIndex; i++) if ((s = JS.SpaceGroup.SG[i]).hmSymbolAlternative != null && s.hmSymbolAlternative.equalsIgnoreCase(nameExt)) return i;

if (haveExtension) {
for (i = 0; i < lastIndex; i++) if ((s = JS.SpaceGroup.SG[i]).hmSymbolAbbr.equalsIgnoreCase(abbr) && s.jmolIdExt.equalsIgnoreCase(ext)) return i;

for (i = 0; i < lastIndex; i++) if ((s = JS.SpaceGroup.SG[i]).hmSymbolAbbrShort.equalsIgnoreCase(abbr) && s.jmolIdExt.equalsIgnoreCase(ext)) return i;

}var uniqueAxis = JS.SpaceGroup.determineUniqueAxis(a, b, c, alpha, beta, gamma);
if (!haveExtension || ext.charAt(0) == '?') for (i = 0; i < lastIndex; i++) if (((s = JS.SpaceGroup.SG[i]).hmSymbolAbbr.equalsIgnoreCase(abbr) || s.hmSymbolAbbrShort.equalsIgnoreCase(abbr) || s.itaNumber.equals(abbr))) switch ((s.ambiguityType).charCodeAt(0)) {
case 0:
return i;
case 97:
if (s.uniqueAxis == uniqueAxis || uniqueAxis == '\0') return i;
break;
case 111:
if (ext.length == 0) {
if (s.hmSymbolExt.equals("2")) return i;
} else if (s.hmSymbolExt.equalsIgnoreCase(ext)) return i;
break;
case 116:
if (ext.length == 0) {
if (s.axisChoice == 'h') return i;
} else if ((s.axisChoice + "").equalsIgnoreCase(ext)) return i;
break;
}

break;
}
if (ext.length == 0) for (i = 0; i < lastIndex; i++) if ((s = JS.SpaceGroup.SG[i]).itaNumber.equals(nameExt)) return i;

return -1;
}, "~S,~N,~N,~N,~N,~N,~N,~N");
Clazz.defineMethod(c$, "setJmolCode", 
function(name){
this.jmolId = name;
var parts = JU.PT.split(name, ":");
this.itaNumber = parts[0];
this.jmolIdExt = (parts.length == 1 ? "" : parts[1]);
this.ambiguityType = '\0';
if (this.jmolIdExt.length > 0) {
var c = this.jmolIdExt.charAt(0);
if (this.jmolIdExt.equals("h") || this.jmolIdExt.equals("r")) {
this.ambiguityType = 't';
this.axisChoice = this.jmolIdExt.charAt(0);
} else if (c == '1' || c == '2') {
this.ambiguityType = 'o';
} else if (this.jmolIdExt.length <= 2 || this.jmolIdExt.length == 3 && c == '-') {
this.ambiguityType = 'a';
this.uniqueAxis = this.jmolIdExt.charAt(c == '-' ? 1 : 0);
} else if (this.jmolIdExt.contains("-")) {
this.ambiguityType = '-';
}}}, "~S");
c$.determineUniqueAxis = Clazz.defineMethod(c$, "determineUniqueAxis", 
function(a, b, c, alpha, beta, gamma){
if (a == b) return (b == c ? '\0' : 'c');
if (b == c) return 'a';
if (c == a) return 'b';
if (alpha == beta) return (beta == gamma ? '\0' : 'c');
if (beta == gamma) return 'a';
if (gamma == alpha) return 'b';
return '\0';
}, "~N,~N,~N,~N,~N,~N");
Clazz.defineMethod(c$, "buildSelf", 
function(sgLineData){
var terms = JU.PT.split(sgLineData.toLowerCase(), ";");
this.jmolId = terms[0].trim();
this.setJmolCode(this.jmolId);
var isAlternate = this.jmolId.endsWith("*");
if (isAlternate) this.jmolId = this.jmolId.substring(0, this.jmolId.length - 1);
this.itaIndex = terms[1].$replace('|', ';');
var s = terms[2];
this.itaTransform = (s.length == 0 || s.equals("--") ? "a,b,c" : JU.PT.rep(s, "ab", "a-b,a+b,c").$replace('|', ';'));
this.clegId = this.itaNumber + ":" + this.itaTransform;
if (terms[3].length > 0) {
this.nHallOperators = Integer.$valueOf(terms[3]);
var lst = JS.SpaceGroup.htByOpCount.get(this.nHallOperators);
if (lst == null) JS.SpaceGroup.htByOpCount.put(this.nHallOperators, lst =  new JU.Lst());
lst.addLast(this);
}this.crystalClass = JS.SpaceGroup.toCap(JU.PT.split(terms[4], "^")[0], 1);
var hm = terms[5];
if (hm.endsWith("*")) hm = hm.substring(0, hm.length - 1);
this.setHMSymbol(hm);
var info;
if ("xyz".equals(terms[6])) {
info = this.hmSymbol;
this.hallSymbol = "" + this.latticeType + "?";
} else {
this.hallSymbol = terms[6];
if (this.hallSymbol.length > 1) this.hallSymbol = JS.SpaceGroup.toCap(this.hallSymbol, 2);
if (isAlternate) {
this.hallSymbolAlt = this.hallSymbol;
this.hallSymbol = JS.SpaceGroup.lastHallSymbol;
}info = this.itaNumber + this.hallSymbol;
if (this.itaNumber.charAt(0) != '0' && info.equals(JS.SpaceGroup.lastInfo)) {
isAlternate = true;
JS.SpaceGroup.ambiguousHMNames += this.hmSymbol + ";";
}}JS.SpaceGroup.lastHallSymbol = this.hallSymbol;
JS.SpaceGroup.lastInfo = info;
this.name = "HM:" + this.hmSymbolFull + " " + (this.hallSymbol == null || this.hallSymbol === "?" ? "[" + this.hallSymbol + "]" : "") + " #" + this.itaIndex;
}, "~S");
Clazz.defineMethod(c$, "setHMSymbol", 
function(name){
var pt = name.indexOf("#");
if (pt >= 0) name = name.substring(0, pt).trim();
this.hmSymbolFull = JS.SpaceGroup.toCap(name, 1);
this.latticeType = this.hmSymbolFull.charAt(0);
var parts = JU.PT.split(this.hmSymbolFull, ":");
this.hmSymbol = parts[0];
this.hmSymbolExt = (parts.length == 1 ? "" : parts[1]);
pt = this.hmSymbol.indexOf(" -3");
if (pt >= 1) if ("admn".indexOf(this.hmSymbol.charAt(pt - 1)) >= 0) {
this.hmSymbolAlternative = (this.hmSymbol.substring(0, pt) + " 3" + this.hmSymbol.substring(pt + 3)).toLowerCase();
}this.hmSymbolAbbr = JU.PT.rep(this.hmSymbol, " ", "");
this.hmSymbolAbbrShort = (this.hmSymbol.length > 3 ? JU.PT.rep(this.hmSymbol, " 1", "") : this.hmSymbolAbbr);
this.hmSymbolAbbrShort = JU.PT.rep(this.hmSymbolAbbrShort, " ", "");
}, "~S");
c$.toCap = Clazz.defineMethod(c$, "toCap", 
function(s, n){
return s.substring(0, n).toUpperCase() + s.substring(n);
}, "~S,~N");
Clazz.defineMethod(c$, "toString", 
function(){
return this.asString();
});
Clazz.defineMethod(c$, "asString", 
function(){
return (this.strName == null ? (this.strName = (this.jmolId == null || this.jmolId.equals("0") ? this.name : this.jmolId + " HM:" + this.hmSymbolFull + " #" + this.clegId)) : this.strName);
});
Clazz.defineMethod(c$, "getDisplayName", 
function(){
if (this.displayName == null) {
var name = null;
if (this.jmolId == null || "--".equals(this.hallSymbol)) {
name = "";
if (this.hmSymbolFull != null && !"--".equals(this.hmSymbol)) name = this.hmSymbolFull + " #";
} else if (!this.jmolId.equals("0")) {
name = this.hmSymbolFull + " #";
}if (name == null) {
name = "[" + this.hallSymbol + "]";
} else {
name += this.clegId;
}if (name.endsWith("2/3a+1/3b+1/3c,-1/3a+1/3b+1/3c,-1/3a-2/3b+1/3c")) name = JU.PT.rep(name, "2/3a+1/3b+1/3c,-1/3a+1/3b+1/3c,-1/3a-2/3b+1/3c", "r");
if (name.indexOf("-- [--]") >= 0) name = "";
if (name.endsWith(":a,b,c")) name = name.substring(0, name.length - 6);
this.displayName = name;
}return this.displayName;
});
c$.getSpaceGroups = Clazz.defineMethod(c$, "getSpaceGroups", 
function(){
if (JS.SpaceGroup.SG == null) {
var n = JS.SpaceGroup.STR_SG.length;
JS.SpaceGroup.nameToGroup =  new java.util.Hashtable();
var defs =  new Array(n);
for (var i = 0; i < n; i++) {
defs[i] =  new JS.SpaceGroup(i, JS.SpaceGroup.STR_SG[i], true);
JS.SpaceGroup.nameToGroup.put(defs[i].jmolId, defs[i]);
}
System.out.println("SpaceGroup - " + JS.SpaceGroup.nSG + " settings generated");
JS.SpaceGroup.STR_SG = null;
JS.SpaceGroup.SG = defs;
}return JS.SpaceGroup.SG;
});
Clazz.defineMethod(c$, "addLatticeVectors", 
function(lattvecs){
if (this.latticeOp >= 0 || lattvecs.size() == 0) return false;
var nOps = this.latticeOp = this.operationCount;
var isMagnetic = (lattvecs.get(0).length == this.modDim + 4);
var magRev = -2;
for (var j = 0; j < lattvecs.size(); j++) {
var data = lattvecs.get(j);
if (isMagnetic) {
magRev = Clazz.floatToInt(data[this.modDim + 3]);
data = JU.AU.arrayCopyF(data, this.modDim + 3);
}if (data.length > this.modDim + 3) return false;
for (var i = 0; i < nOps; i++) {
var newOp =  new JS.SymmetryOperation(null, 0, true);
newOp.modDim = this.modDim;
var op = this.operations[i];
newOp.divisor = op.divisor;
newOp.linearRotTrans = JU.AU.arrayCopyF(op.linearRotTrans, -1);
newOp.setFromMatrix(data, false);
if (magRev != -2) newOp.setTimeReversal(op.timeReversal * magRev);
newOp.xyzOriginal = newOp.xyz;
this.addOp(newOp, newOp.xyz, true);
}
}
return true;
}, "JU.Lst");
Clazz.defineMethod(c$, "getSiteMultiplicity", 
function(pt, unitCell){
var n = this.finalOperations.length;
var pts =  new JU.Lst();
for (var i = n; --i >= 0; ) {
var pt1 = JU.P3.newP(pt);
this.finalOperations[i].rotTrans(pt1);
unitCell.unitize(pt1);
for (var j = pts.size(); --j >= 0; ) {
var pt0 = pts.get(j);
if (pt1.distanceSquared(pt0) < 1.96E-6) {
pt1 = null;
break;
}}
if (pt1 != null) pts.addLast(pt1);
}
return Clazz.doubleToInt(n / pts.size());
}, "JU.P3,JS.UnitCell");
Clazz.defineMethod(c$, "setName", 
function(name){
this.name = name;
if (name != null && name.startsWith("HM:")) {
this.setHMSymbol(name.substring(3));
}this.strName = this.displayName = null;
}, "~S");
Clazz.defineMethod(c$, "getNameType", 
function(type, uc){
var ret = null;
if (type.equals("HM")) {
ret = this.hmSymbol;
} else if (type.equals("ITA")) {
ret = this.itaNumber;
} else if (type.equals("Hall")) {
ret = this.hallSymbol;
} else {
ret = "?";
}if (ret != null) return ret;
if (this.info == null) this.info = JS.SpaceGroup.getInfo(this, this.hmSymbol, uc.getUnitCellParams(), true, false);
if ((typeof(this.info)=='string')) return null;
var map = this.info;
var v = map.get(type.equals("Hall") ? "HallSymbol" : type.equals("ITA") ? "ita" : "HermannMauguinSymbol");
return (v == null ? null : v.toString());
}, "~S,J.api.SymmetryInterface");
c$.getSpaceGroupFromJmolClegOrITA = Clazz.defineMethod(c$, "getSpaceGroupFromJmolClegOrITA", 
function(name){
var n = JS.SpaceGroup.SG.length;
if (name.indexOf(":") >= 0) {
if (name.indexOf(",") >= 0) {
for (var i = 0; i < n; i++) if (name.equals(JS.SpaceGroup.SG[i].clegId)) return JS.SpaceGroup.SG[i];

} else {
for (var i = 0; i < n; i++) if (name.equals(JS.SpaceGroup.SG[i].jmolId)) return JS.SpaceGroup.SG[i];

}} else if (name.indexOf(".") >= 0) {
for (var i = 0; i < n; i++) if (name.equals(JS.SpaceGroup.SG[i].itaIndex)) return JS.SpaceGroup.SG[i];

} else {
for (var i = 0; i < n; i++) if (name.equals(JS.SpaceGroup.SG[i].itaNumber)) return JS.SpaceGroup.SG[i];

}return null;
}, "~S");
Clazz.defineMethod(c$, "checkHallOperators", 
function(){
if (this.nHallOperators != null && this.nHallOperators.intValue() != this.operationCount) {
if (this.hallInfo == null || this.hallInfo.nRotations > 0) {
this.generateAllOperators(this.hallInfo);
} else {
this.init(false);
this.doNormalize = false;
JS.SpaceGroup.transformSpaceGroup(this, JS.SpaceGroup.getSpaceGroupFromJmolClegOrITA(this.itaNumber), null, this.itaTransform, null);
this.hallInfo = null;
}}});
Clazz.defineMethod(c$, "getOpsCtr", 
function(transform){
var sg = JS.SpaceGroup.getNull(true, true, false);
JS.SpaceGroup.transformSpaceGroup(sg, this, null, "!" + transform, null);
sg.setFinalOperations();
var sg2 = JS.SpaceGroup.getNull(true, false, false);
JS.SpaceGroup.transformSpaceGroup(sg2, sg, null, transform, null);
sg2.setFinalOperations();
return sg2.finalOperations;
}, "~S");
c$.getSpaceGroupFromIndex = Clazz.defineMethod(c$, "getSpaceGroupFromIndex", 
function(i){
return (JS.SpaceGroup.SG != null && i >= 0 && i < JS.SpaceGroup.SG.length ? JS.SpaceGroup.SG[i] : null);
}, "~N");
Clazz.defineMethod(c$, "setITATableNames", 
function(jmolId, sg, set, tr){
this.itaNumber = sg;
this.itaIndex = (tr != null ? sg + ":" + tr : set.indexOf(".") >= 0 ? set : sg + "." + set);
this.itaTransform = tr;
this.clegId = sg + ":" + tr;
this.jmolId = jmolId;
if (jmolId == null) {
this.info = this.dumpInfoObj();
} else {
this.setJmolCode(jmolId);
}}, "~S,~S,~S,~S");
c$.transformCoords = Clazz.defineMethod(c$, "transformCoords", 
function(coord, trmInv, centering, t, v, coordt){
if (coordt == null) coordt =  new JU.Lst();
for (var j = 0, n = coord.size(); j < n; j++) {
var xyz = JS.SymmetryOperation.transformStr(coord.get(j), null, trmInv, t, v, null, centering, true, true);
if (!coordt.contains(xyz)) coordt.addLast(xyz);
}
return coordt;
}, "JU.Lst,JU.M4,JU.P3,JU.M4,~A,JU.Lst");
c$.getTransformRange = Clazz.defineMethod(c$, "getTransformRange", 
function(trm){
var t =  Clazz.newFloatArray (2, 3, 0);
var row =  Clazz.newFloatArray (4, 0);
for (var i = 0; i < 3; i++) {
trm.getRow(i, row);
for (var j = 0; j < 3; j++) {
var v = row[j];
if (v < 0) {
t[0][i] += -row[j];
} else if (v > 0) {
t[1][i] += row[j];
}}
}
var ignore = true;
for (var i = 0, dz = 0; i < 2; i++, dz++) {
for (var j = 0; j < 3; j++) {
var d = Clazz.doubleToInt(Math.ceil(t[i][j]));
if (d > dz) ignore = false;
t[i][j] = (i == 0 ? -d : d);
}
}
return (ignore ? null : t);
}, "JU.M4");
c$.getTransformedCentering = Clazz.defineMethod(c$, "getTransformedCentering", 
function(trm, cent){
var trmInv = JU.M4.newM4(trm);
trmInv.invert();
var n0 = cent.size();
var p =  new JU.P3();
var c = JS.SpaceGroup.getTransformRange(trm);
if (c != null) {
for (var i = Clazz.floatToInt(c[0][0]); i < c[1][0]; i++) {
for (var j = Clazz.floatToInt(c[0][1]); j <= c[1][1]; j++) {
for (var k = Clazz.floatToInt(c[0][2]); k <= c[1][2]; k++) {
p.set(i, j, k);
trmInv.rotTrans(p);
if (p.length() % 1 != 0) {
p.x = p.x % 1;
p.y = p.y % 1;
p.z = p.z % 1;
var s = JS.SymmetryOperation.norm3(p);
if (!s.equals("0,0,0") && !cent.contains(s)) cent.addLast(s);
}}
}
}
var n = cent.size();
if (n > 0) {
var a =  new Array(n);
cent.toArray(a);
java.util.Arrays.sort(a);
cent.clear();
for (var i = 0; i < n; i++) cent.addLast(a[i]);

}}for (var i = n0; --i >= 0; ) {
JS.SymmetryOperation.toPoint(cent.get(i), p);
trmInv.rotTrans(p);
if (p.x % 1 == 0 && p.y % 1 == 0 && p.z % 1 == 0) cent.remove(i);
}
return trmInv;
}, "JU.M4,JU.Lst");
c$.fillMoreData = Clazz.defineMethod(c$, "fillMoreData", 
function(map, clegId, itno, its0){
var pt = clegId.indexOf(':');
var transform = (pt < 0 ? "a,b,c" : clegId.substring(pt + 1));
var trm = JS.UnitCell.toTrm(transform, null);
var gp0 = its0.get("gp");
var wpos0 = its0.get("wpos");
var cent0 = wpos0.get("cent");
var cent =  new JU.Lst();
if (cent0 != null) cent.addAll(cent0);
var nctr0 = cent.size();
var trmInv = JS.SpaceGroup.getTransformedCentering(trm, cent);
var nctr = cent.size();
var pos0 = wpos0.get("pos");
var pos =  new JU.Lst();
var t =  new JU.M4();
var v =  Clazz.newFloatArray (16, 0);
var f = (nctr + 1) / (nctr0 + 1);
for (var i = 0, n = pos0.size(); i < n; i++) {
var p0 = pos0.get(i);
var p =  new java.util.Hashtable();
p.putAll(p0);
var coord = p0.get("coord");
if (coord != null) {
coord = JS.SpaceGroup.transformCoords(coord, trmInv, null, t, v, null);
p.put("coord", coord);
}var mult = (p0.get("mult")).intValue();
p.put("mult", Integer.$valueOf(Clazz.floatToInt(mult * f)));
pos.addLast(p);
}
var gp =  new JU.Lst();
JS.SpaceGroup.transformCoords(gp0, trmInv, null, t, v, gp);
if (nctr > 0) {
for (var i = 0; i < nctr; i++) {
var p =  new JU.P3();
JS.SpaceGroup.transformCoords(gp0, trmInv, JS.SymmetryOperation.toPoint(cent.get(i), p), t, v, gp);
}
}if (map == null) {
map =  new java.util.Hashtable();
map.put("sg", Integer.$valueOf(itno));
map.put("trm", transform);
map.put("clegId", itno + ":" + transform);
map.put("det", Float.$valueOf(trm.determinant3()));
} else {
map.remove("more");
}var wpos =  new java.util.Hashtable();
if (nctr > 0) wpos.put("cent", cent);
wpos.put("pos", pos);
map.put("wpos", wpos);
wpos.put("gp", gp);
gp =  new JU.Lst();
var base = JS.SpaceGroup.getSpaceGroupFromJmolClegOrITA(clegId);
var sg = JS.SpaceGroup.transformSpaceGroup(null, base, gp0, transform,  new JU.M4());
for (var i = 0, n = sg.getOperationCount(); i < n; i++) {
gp.addLast((sg.getOperation(i)).xyz);
}
map.put("gp", gp);
return map;
}, "java.util.Map,~S,~N,java.util.Map");
c$.transformSpaceGroup = Clazz.defineMethod(c$, "transformSpaceGroup", 
function(sg, base, genPos, transform, trm){
if (genPos == null) {
base.setFinalOperations();
genPos =  new JU.Lst();
for (var i = 0, n = base.getOperationCount(); i < n; i++) {
genPos.addLast(base.getXyz(i, false));
}
}var normalize = (sg == null || sg.doNormalize);
var xyzList = JS.SpaceGroup.addTransformXYZList(sg, genPos, transform, trm, normalize);
if (sg == null) {
return JS.SpaceGroup.createITASpaceGroup(xyzList, base);
}if (transform == null) {
sg.setFrom(base, true);
} else {
sg.setITATableNames(sg.jmolId, sg.itaNumber, "1", transform);
}return sg;
}, "JS.SpaceGroup,JS.SpaceGroup,JU.Lst,~S,JU.M4");
c$.createITASpaceGroup = Clazz.defineMethod(c$, "createITASpaceGroup", 
function(genpos, base){
var sg =  new JS.SpaceGroup(-1, "0;--;--;0;--;--;--", true);
sg.doNormalize = false;
for (var i = 0, n = genpos.size(); i < n; i++) {
var op =  new JS.SymmetryOperation(null, i, false);
var xyz = genpos.get(i);
op.setMatrixFromXYZ(xyz, 0, false);
sg.addOp(op, xyz, false);
}
if (base != null) sg.setFrom(base, true);
return sg;
}, "JU.Lst,JS.SpaceGroup");
c$.addTransformXYZList = Clazz.defineMethod(c$, "addTransformXYZList", 
function(sg, genPos, transform, trm, normalize){
var trmInv = null;
var t = null;
var v = null;
if (transform != null) {
if (transform.equals("r")) transform = "2/3a+1/3b+1/3c,-1/3a+1/3b+1/3c,-1/3a-2/3b+1/3c";
trm = JS.UnitCell.toTrm(transform, trm);
trmInv = JU.M4.newM4(trm);
trmInv.invert();
v =  Clazz.newFloatArray (16, 0);
t =  new JU.M4();
}var xyzList = JS.SpaceGroup.addTransformedOperations(sg, genPos, trm, trmInv, t, v, sg == null ?  new JU.Lst() : null, null, normalize);
if (sg == null) return xyzList;
var c = JS.SpaceGroup.getTransformRange(trm);
if (c != null) {
var p =  new JU.P3();
for (var i = Clazz.floatToInt(c[0][0]); i < c[1][0]; i++) {
for (var j = Clazz.floatToInt(c[0][1]); j <= c[1][1]; j++) {
for (var k = Clazz.floatToInt(c[0][2]); k <= c[1][2]; k++) {
if (i == 0 && j == 0 && k == 0) continue;
p.set(i, j, k);
JS.SpaceGroup.addTransformedOperations(sg, genPos, trm, trmInv, t, v, null, p, normalize);
}
}
}
}return null;
}, "JS.SpaceGroup,JU.Lst,~S,JU.M4,~B");
c$.addTransformedOperations = Clazz.defineMethod(c$, "addTransformedOperations", 
function(sg, genPos, trm, trmInv, t, v, retGenPos, centering, normalize){
if (sg != null) sg.latticeOp = 0;
for (var i = 0, c = genPos.size(); i < c; i++) {
var xyz = genPos.get(i);
if (trm != null && (i > 0 || centering != null)) {
xyz = JS.SymmetryOperation.transformStr(xyz, trm, trmInv, t, v, centering, null, normalize, false);
}if (sg == null) {
retGenPos.addLast(xyz);
} else {
sg.addOperation(xyz, 0, false);
}}
return retGenPos;
}, "JS.SpaceGroup,JU.Lst,JU.M4,JU.M4,JU.M4,~A,JU.Lst,JU.P3,~B");
c$.canonicalSeitzList = null;
c$.sgIndex = -1;
c$.lastInfo = null;
c$.ambiguousHMNames = "";
c$.lastHallSymbol = "";
c$.SG = null;
c$.htByOpCount =  new java.util.Hashtable();
c$.nameToGroup = null;
c$.nSG = 0;
c$.STR_SG =  Clazz.newArray(-1, ["1;1.1;;1;c1^1;p 1;p 1", "2;2.1;;2;ci^1;p -1;-p 1", "3:b;3.1;;2;c2^1;p 1 2 1;p 2y", "3:b;3.1;;2;c2^1;p 2;p 2y", "3:c;3.2;c,a,b;2;c2^1;p 1 1 2;p 2", "3:a;3.3;b,c,a;2;c2^1;p 2 1 1;p 2x", "4:b;4.1;;2;c2^2;p 1 21 1;p 2yb", "4:b;4.1;;2;c2^2;p 21;p 2yb", "4:b*;4.1;;2;c2^2;p 1 21 1*;p 2y1", "4:c;4.2;c,a,b;2;c2^2;p 1 1 21;p 2c", "4:c*;4.2;c,a,b;2;c2^2;p 1 1 21*;p 21", "4:a;4.3;b,c,a;2;c2^2;p 21 1 1;p 2xa", "4:a*;4.3;b,c,a;2;c2^2;p 21 1 1*;p 2x1", "5:b1;5.1;;4;c2^3;c 1 2 1;c 2y", "5:b1;5.1;;4;c2^3;c 2;c 2y", "5:b2;5.2;-a-c,b,a;4;c2^3;a 1 2 1;a 2y", "5:b3;5.3;c,b,-a-c;4;c2^3;i 1 2 1;i 2y", "5:c1;5.4;c,a,b;4;c2^3;a 1 1 2;a 2", "5:c2;5.5;a,-a-c,b;4;c2^3;b 1 1 2;b 2", "5:c3;5.6;-a-c,c,b;4;c2^3;i 1 1 2;i 2", "5:a1;5.7;b,c,a;4;c2^3;b 2 1 1;b 2x", "5:a2;5.8;b,a,-a-c;4;c2^3;c 2 1 1;c 2x", "5:a3;5.9;b,-a-c,c;4;c2^3;i 2 1 1;i 2x", "6:b;6.1;;2;cs^1;p 1 m 1;p -2y", "6:b;6.1;;2;cs^1;p m;p -2y", "6:c;6.2;c,a,b;2;cs^1;p 1 1 m;p -2", "6:a;6.3;b,c,a;2;cs^1;p m 1 1;p -2x", "7:b1;7.1;;2;cs^2;p 1 c 1;p -2yc", "7:b1;7.1;;2;cs^2;p c;p -2yc", "7:b2;7.2;-a-c,b,a;2;cs^2;p 1 n 1;p -2yac", "7:b2;7.2;-a-c,b,a;2;cs^2;p n;p -2yac", "7:b3;7.3;c,b,-a-c;2;cs^2;p 1 a 1;p -2ya", "7:b3;7.3;c,b,-a-c;2;cs^2;p a;p -2ya", "7:c1;7.4;c,a,b;2;cs^2;p 1 1 a;p -2a", "7:c2;7.5;a,-a-c,b;2;cs^2;p 1 1 n;p -2ab", "7:c3;7.6;-a-c,c,b;2;cs^2;p 1 1 b;p -2b", "7:a1;7.7;b,c,a;2;cs^2;p b 1 1;p -2xb", "7:a2;7.8;b,a,-a-c;2;cs^2;p n 1 1;p -2xbc", "7:a3;7.9;b,-a-c,c;2;cs^2;p c 1 1;p -2xc", "8:b1;8.1;;4;cs^3;c 1 m 1;c -2y", "8:b1;8.1;;4;cs^3;c m;c -2y", "8:b2;8.2;-a-c,b,a;4;cs^3;a 1 m 1;a -2y", "8:b3;8.3;c,b,-a-c;4;cs^3;i 1 m 1;i -2y", "8:b3;8.3;c,b,-a-c;4;cs^3;i m;i -2y", "8:c1;8.4;c,a,b;4;cs^3;a 1 1 m;a -2", "8:c2;8.5;a,-a-c,b;4;cs^3;b 1 1 m;b -2", "8:c3;8.6;-a-c,c,b;4;cs^3;i 1 1 m;i -2", "8:a1;8.7;b,c,a;4;cs^3;b m 1 1;b -2x", "8:a2;8.8;b,a,-a-c;4;cs^3;c m 1 1;c -2x", "8:a3;8.9;b,-a-c,c;4;cs^3;i m 1 1;i -2x", "9:b1;9.1;;4;cs^4;c 1 c 1;c -2yc", "9:b1;9.1;;4;cs^4;c c;c -2yc", "9:b2;9.2;-a-c,b,a;4;cs^4;a 1 n 1;a -2yab", "9:b3;9.3;c,b,-a-c;4;cs^4;i 1 a 1;i -2ya", "9:-b1;9.4;c,-b,a;4;cs^4;a 1 a 1;a -2ya", "9:-b2;9.5;a,-b,-a-c;4;cs^4;c 1 n 1;c -2yac", "9:-b3;9.6;-a-c,-b,c;4;cs^4;i 1 c 1;i -2yc", "9:c1;9.7;c,a,b;4;cs^4;a 1 1 a;a -2a", "9:c2;9.8;a,-a-c,b;4;cs^4;b 1 1 n;b -2ab", "9:c3;9.9;-a-c,c,b;4;cs^4;i 1 1 b;i -2b", "9:-c1;9.10;a,c,-b;4;cs^4;b 1 1 b;b -2b", "9:-c2;9.11;-a-c,a,-b;4;cs^4;a 1 1 n;a -2ab", "9:-c3;9.12;c,-a-c,-b;4;cs^4;i 1 1 a;i -2a", "9:a1;9.13;b,c,a;4;cs^4;b b 1 1;b -2xb", "9:a2;9.14;b,a,-a-c;4;cs^4;c n 1 1;c -2xac", "9:a3;9.15;b,-a-c,c;4;cs^4;i c 1 1;i -2xc", "9:-a1;9.16;-b,a,c;4;cs^4;c c 1 1;c -2xc", "9:-a2;9.17;-b,-a-c,a;4;cs^4;b n 1 1;b -2xab", "9:-a3;9.18;-b,c,-a-c;4;cs^4;i b 1 1;i -2xb", "10:b;10.1;;4;c2h^1;p 1 2/m 1;-p 2y", "10:b;10.1;;4;c2h^1;p 2/m;-p 2y", "10:c;10.2;c,a,b;4;c2h^1;p 1 1 2/m;-p 2", "10:a;10.3;b,c,a;4;c2h^1;p 2/m 1 1;-p 2x", "11:b;11.1;;4;c2h^2;p 1 21/m 1;-p 2yb", "11:b;11.1;;4;c2h^2;p 21/m;-p 2yb", "11:b*;11.1;;4;c2h^2;p 1 21/m 1*;-p 2y1", "11:c;11.2;c,a,b;4;c2h^2;p 1 1 21/m;-p 2c", "11:c*;11.2;c,a,b;4;c2h^2;p 1 1 21/m*;-p 21", "11:a;11.3;b,c,a;4;c2h^2;p 21/m 1 1;-p 2xa", "11:a*;11.3;b,c,a;4;c2h^2;p 21/m 1 1*;-p 2x1", "12:b1;12.1;;8;c2h^3;c 1 2/m 1;-c 2y", "12:b1;12.1;;8;c2h^3;c 2/m;-c 2y", "12:b2;12.2;-a-c,b,a;8;c2h^3;a 1 2/m 1;-a 2y", "12:b3;12.3;c,b,-a-c;8;c2h^3;i 1 2/m 1;-i 2y", "12:b3;12.3;c,b,-a-c;8;c2h^3;i 2/m;-i 2y", "12:c1;12.4;c,a,b;8;c2h^3;a 1 1 2/m;-a 2", "12:c2;12.5;a,-a-c,b;8;c2h^3;b 1 1 2/m;-b 2", "12:c3;12.6;-a-c,c,b;8;c2h^3;i 1 1 2/m;-i 2", "12:a1;12.7;b,c,a;8;c2h^3;b 2/m 1 1;-b 2x", "12:a2;12.8;b,a,-a-c;8;c2h^3;c 2/m 1 1;-c 2x", "12:a3;12.9;b,-a-c,c;8;c2h^3;i 2/m 1 1;-i 2x", "13:b1;13.1;;4;c2h^4;p 1 2/c 1;-p 2yc", "13:b1;13.1;;4;c2h^4;p 2/c;-p 2yc", "13:b2;13.2;-a-c,b,a;4;c2h^4;p 1 2/n 1;-p 2yac", "13:b2;13.2;-a-c,b,a;4;c2h^4;p 2/n;-p 2yac", "13:b3;13.3;c,b,-a-c;4;c2h^4;p 1 2/a 1;-p 2ya", "13:b3;13.3;c,b,-a-c;4;c2h^4;p 2/a;-p 2ya", "13:c1;13.4;c,a,b;4;c2h^4;p 1 1 2/a;-p 2a", "13:c2;13.5;a,-a-c,b;4;c2h^4;p 1 1 2/n;-p 2ab", "13:c3;13.6;-a-c,c,b;4;c2h^4;p 1 1 2/b;-p 2b", "13:a1;13.7;b,c,a;4;c2h^4;p 2/b 1 1;-p 2xb", "13:a2;13.8;b,a,-a-c;4;c2h^4;p 2/n 1 1;-p 2xbc", "13:a3;13.9;b,-a-c,c;4;c2h^4;p 2/c 1 1;-p 2xc", "14:b1;14.1;;4;c2h^5;p 1 21/c 1;-p 2ybc", "14:b1;14.1;;4;c2h^5;p 21/c;-p 2ybc", "14:b2;14.2;-a-c,b,a;4;c2h^5;p 1 21/n 1;-p 2yn", "14:b2;14.2;-a-c,b,a;4;c2h^5;p 21/n;-p 2yn", "14:b3;14.3;c,b,-a-c;4;c2h^5;p 1 21/a 1;-p 2yab", "14:b3;14.3;c,b,-a-c;4;c2h^5;p 21/a;-p 2yab", "14:c1;14.4;c,a,b;4;c2h^5;p 1 1 21/a;-p 2ac", "14:c2;14.5;a,-a-c,b;4;c2h^5;p 1 1 21/n;-p 2n", "14:c3;14.6;-a-c,c,b;4;c2h^5;p 1 1 21/b;-p 2bc", "14:a1;14.7;b,c,a;4;c2h^5;p 21/b 1 1;-p 2xab", "14:a2;14.8;b,a,-a-c;4;c2h^5;p 21/n 1 1;-p 2xn", "14:a3;14.9;b,-a-c,c;4;c2h^5;p 21/c 1 1;-p 2xac", "15:b1;15.1;;8;c2h^6;c 1 2/c 1;-c 2yc", "15:b1;15.1;;8;c2h^6;c 2/c;-c 2yc", "15:b2;15.2;-a-c,b,a;8;c2h^6;a 1 2/n 1;-a 2yab", "15:b3;15.3;c,b,-a-c;8;c2h^6;i 1 2/a 1;-i 2ya", "15:b3;15.3;c,b,-a-c;8;c2h^6;i 2/a;-i 2ya", "15:-b1;15.4;c,-b,a;8;c2h^6;a 1 2/a 1;-a 2ya", "15:-b2;15.5;a,-b,-a-c;8;c2h^6;c 1 2/n 1;-c 2yac", "15:-b2;15.5;a,-b,-a-c;8;c2h^6;c 2/n;-c 2yac", "15:-b3;15.6;-a-c,-b,c;8;c2h^6;i 1 2/c 1;-i 2yc", "15:-b3;15.6;-a-c,-b,c;8;c2h^6;i 2/c;-i 2yc", "15:c1;15.7;c,a,b;8;c2h^6;a 1 1 2/a;-a 2a", "15:c2;15.8;a,-a-c,b;8;c2h^6;b 1 1 2/n;-b 2ab", "15:c3;15.9;-a-c,c,b;8;c2h^6;i 1 1 2/b;-i 2b", "15:-c1;15.10;a,c,-b;8;c2h^6;b 1 1 2/b;-b 2b", "15:-c2;15.11;-a-c,a,-b;8;c2h^6;a 1 1 2/n;-a 2ab", "15:-c3;15.12;c,-a-c,-b;8;c2h^6;i 1 1 2/a;-i 2a", "15:a1;15.13;b,c,a;8;c2h^6;b 2/b 1 1;-b 2xb", "15:a2;15.14;b,a,-a-c;8;c2h^6;c 2/n 1 1;-c 2xac", "15:a3;15.15;b,-a-c,c;8;c2h^6;i 2/c 1 1;-i 2xc", "15:-a1;15.16;-b,a,c;8;c2h^6;c 2/c 1 1;-c 2xc", "15:-a2;15.17;-b,-a-c,a;8;c2h^6;b 2/n 1 1;-b 2xab", "15:-a3;15.18;-b,c,-a-c;8;c2h^6;i 2/b 1 1;-i 2xb", "16;16.1;;4;d2^1;p 2 2 2;p 2 2", "17;17.1;;4;d2^2;p 2 2 21;p 2c 2", "17*;17.1;;4;d2^2;p 2 2 21*;p 21 2", "17:cab;17.2;c,a,b;4;d2^2;p 21 2 2;p 2a 2a", "17:bca;17.3;b,c,a;4;d2^2;p 2 21 2;p 2 2b", "18;18.1;;4;d2^3;p 21 21 2;p 2 2ab", "18:cab;18.2;c,a,b;4;d2^3;p 2 21 21;p 2bc 2", "18:bca;18.3;b,c,a;4;d2^3;p 21 2 21;p 2ac 2ac", "19;19.1;;4;d2^4;p 21 21 21;p 2ac 2ab", "20;20.1;;8;d2^5;c 2 2 21;c 2c 2", "20*;20.1;;8;d2^5;c 2 2 21*;c 21 2", "20:cab;20.2;c,a,b;8;d2^5;a 21 2 2;a 2a 2a", "20:cab*;20.2;c,a,b;8;d2^5;a 21 2 2*;a 2a 21", "20:bca;20.3;b,c,a;8;d2^5;b 2 21 2;b 2 2b", "21;21.1;;8;d2^6;c 2 2 2;c 2 2", "21:cab;21.2;c,a,b;8;d2^6;a 2 2 2;a 2 2", "21:bca;21.3;b,c,a;8;d2^6;b 2 2 2;b 2 2", "22;22.1;;16;d2^7;f 2 2 2;f 2 2", "23;23.1;;8;d2^8;i 2 2 2;i 2 2", "24;24.1;;8;d2^9;i 21 21 21;i 2b 2c", "25;25.1;;4;c2v^1;p m m 2;p 2 -2", "25:cab;25.2;c,a,b;4;c2v^1;p 2 m m;p -2 2", "25:bca;25.3;b,c,a;4;c2v^1;p m 2 m;p -2 -2", "26;26.1;;4;c2v^2;p m c 21;p 2c -2", "26*;26.1;;4;c2v^2;p m c 21*;p 21 -2", "26:ba-c;26.2;b,a,-c;4;c2v^2;p c m 21;p 2c -2c", "26:ba-c*;26.2;b,a,-c;4;c2v^2;p c m 21*;p 21 -2c", "26:cab;26.3;c,a,b;4;c2v^2;p 21 m a;p -2a 2a", "26:-cba;26.4;-c,b,a;4;c2v^2;p 21 a m;p -2 2a", "26:bca;26.5;b,c,a;4;c2v^2;p b 21 m;p -2 -2b", "26:a-cb;26.6;a,-c,b;4;c2v^2;p m 21 b;p -2b -2", "27;27.1;;4;c2v^3;p c c 2;p 2 -2c", "27:cab;27.2;c,a,b;4;c2v^3;p 2 a a;p -2a 2", "27:bca;27.3;b,c,a;4;c2v^3;p b 2 b;p -2b -2b", "28;28.1;;4;c2v^4;p m a 2;p 2 -2a", "28*;28.1;;4;c2v^4;p m a 2*;p 2 -21", "28:ba-c;28.2;b,a,-c;4;c2v^4;p b m 2;p 2 -2b", "28:cab;28.3;c,a,b;4;c2v^4;p 2 m b;p -2b 2", "28:-cba;28.4;-c,b,a;4;c2v^4;p 2 c m;p -2c 2", "28:-cba*;28.4;-c,b,a;4;c2v^4;p 2 c m*;p -21 2", "28:bca;28.5;b,c,a;4;c2v^4;p c 2 m;p -2c -2c", "28:a-cb;28.6;a,-c,b;4;c2v^4;p m 2 a;p -2a -2a", "29;29.1;;4;c2v^5;p c a 21;p 2c -2ac", "29:ba-c;29.2;b,a,-c;4;c2v^5;p b c 21;p 2c -2b", "29:cab;29.3;c,a,b;4;c2v^5;p 21 a b;p -2b 2a", "29:-cba;29.4;-c,b,a;4;c2v^5;p 21 c a;p -2ac 2a", "29:bca;29.5;b,c,a;4;c2v^5;p c 21 b;p -2bc -2c", "29:a-cb;29.6;a,-c,b;4;c2v^5;p b 21 a;p -2a -2ab", "30;30.1;;4;c2v^6;p n c 2;p 2 -2bc", "30:ba-c;30.2;b,a,-c;4;c2v^6;p c n 2;p 2 -2ac", "30:cab;30.3;c,a,b;4;c2v^6;p 2 n a;p -2ac 2", "30:-cba;30.4;-c,b,a;4;c2v^6;p 2 a n;p -2ab 2", "30:bca;30.5;b,c,a;4;c2v^6;p b 2 n;p -2ab -2ab", "30:a-cb;30.6;a,-c,b;4;c2v^6;p n 2 b;p -2bc -2bc", "31;31.1;;4;c2v^7;p m n 21;p 2ac -2", "31:ba-c;31.2;b,a,-c;4;c2v^7;p n m 21;p 2bc -2bc", "31:cab;31.3;c,a,b;4;c2v^7;p 21 m n;p -2ab 2ab", "31:-cba;31.4;-c,b,a;4;c2v^7;p 21 n m;p -2 2ac", "31:bca;31.5;b,c,a;4;c2v^7;p n 21 m;p -2 -2bc", "31:a-cb;31.6;a,-c,b;4;c2v^7;p m 21 n;p -2ab -2", "32;32.1;;4;c2v^8;p b a 2;p 2 -2ab", "32:cab;32.2;c,a,b;4;c2v^8;p 2 c b;p -2bc 2", "32:bca;32.3;b,c,a;4;c2v^8;p c 2 a;p -2ac -2ac", "33;33.1;;4;c2v^9;p n a 21;p 2c -2n", "33*;33.1;;4;c2v^9;p n a 21*;p 21 -2n", "33:ba-c;33.2;b,a,-c;4;c2v^9;p b n 21;p 2c -2ab", "33:ba-c*;33.2;b,a,-c;4;c2v^9;p b n 21*;p 21 -2ab", "33:cab;33.3;c,a,b;4;c2v^9;p 21 n b;p -2bc 2a", "33:cab*;33.3;c,a,b;4;c2v^9;p 21 n b*;p -2bc 21", "33:-cba;33.4;-c,b,a;4;c2v^9;p 21 c n;p -2n 2a", "33:-cba*;33.4;-c,b,a;4;c2v^9;p 21 c n*;p -2n 21", "33:bca;33.5;b,c,a;4;c2v^9;p c 21 n;p -2n -2ac", "33:a-cb;33.6;a,-c,b;4;c2v^9;p n 21 a;p -2ac -2n", "34;34.1;;4;c2v^10;p n n 2;p 2 -2n", "34:cab;34.2;c,a,b;4;c2v^10;p 2 n n;p -2n 2", "34:bca;34.3;b,c,a;4;c2v^10;p n 2 n;p -2n -2n", "35;35.1;;8;c2v^11;c m m 2;c 2 -2", "35:cab;35.2;c,a,b;8;c2v^11;a 2 m m;a -2 2", "35:bca;35.3;b,c,a;8;c2v^11;b m 2 m;b -2 -2", "36;36.1;;8;c2v^12;c m c 21;c 2c -2", "36*;36.1;;8;c2v^12;c m c 21*;c 21 -2", "36:ba-c;36.2;b,a,-c;8;c2v^12;c c m 21;c 2c -2c", "36:ba-c*;36.2;b,a,-c;8;c2v^12;c c m 21*;c 21 -2c", "36:cab;36.3;c,a,b;8;c2v^12;a 21 m a;a -2a 2a", "36:cab*;36.3;c,a,b;8;c2v^12;a 21 m a*;a -2a 21", "36:-cba;36.4;-c,b,a;8;c2v^12;a 21 a m;a -2 2a", "36:-cba*;36.4;-c,b,a;8;c2v^12;a 21 a m*;a -2 21", "36:bca;36.5;b,c,a;8;c2v^12;b b 21 m;b -2 -2b", "36:a-cb;36.6;a,-c,b;8;c2v^12;b m 21 b;b -2b -2", "37;37.1;;8;c2v^13;c c c 2;c 2 -2c", "37:cab;37.2;c,a,b;8;c2v^13;a 2 a a;a -2a 2", "37:bca;37.3;b,c,a;8;c2v^13;b b 2 b;b -2b -2b", "38;38.1;;8;c2v^14;a m m 2;a 2 -2", "38:ba-c;38.2;b,a,-c;8;c2v^14;b m m 2;b 2 -2", "38:cab;38.3;c,a,b;8;c2v^14;b 2 m m;b -2 2", "38:-cba;38.4;-c,b,a;8;c2v^14;c 2 m m;c -2 2", "38:bca;38.5;b,c,a;8;c2v^14;c m 2 m;c -2 -2", "38:a-cb;38.6;a,-c,b;8;c2v^14;a m 2 m;a -2 -2", "39;39.1;;8;c2v^15;a e m 2;a 2 -2b", "39;39.1;;8;c2v^15;a b m 2;a 2 -2b", "39:ba-c;39.2;b,a,-c;8;c2v^15;b m e 2;b 2 -2a", "39:ba-c;39.2;b,a,-c;8;c2v^15;b m a 2;b 2 -2a", "39:cab;39.3;c,a,b;8;c2v^15;b 2 e m;b -2a 2", "39:cab;39.3;c,a,b;8;c2v^15;b 2 c m;b -2a 2", "39:-cba;39.4;-c,b,a;8;c2v^15;c 2 m e;c -2a 2", "39:-cba;39.4;-c,b,a;8;c2v^15;c 2 m b;c -2a 2", "39:bca;39.5;b,c,a;8;c2v^15;c m 2 e;c -2a -2a", "39:bca;39.5;b,c,a;8;c2v^15;c m 2 a;c -2a -2a", "39:a-cb;39.6;a,-c,b;8;c2v^15;a e 2 m;a -2b -2b", "39:a-cb;39.6;a,-c,b;8;c2v^15;a c 2 m;a -2b -2b", "40;40.1;;8;c2v^16;a m a 2;a 2 -2a", "40:ba-c;40.2;b,a,-c;8;c2v^16;b b m 2;b 2 -2b", "40:cab;40.3;c,a,b;8;c2v^16;b 2 m b;b -2b 2", "40:-cba;40.4;-c,b,a;8;c2v^16;c 2 c m;c -2c 2", "40:bca;40.5;b,c,a;8;c2v^16;c c 2 m;c -2c -2c", "40:a-cb;40.6;a,-c,b;8;c2v^16;a m 2 a;a -2a -2a", "41;41.1;;8;c2v^17;a e a 2;a 2 -2ab", "41;41.1;;8;c2v^17;a b a 2;a 2 -2ab", "41:ba-c;41.2;b,a,-c;8;c2v^17;b b e 2;b 2 -2ab", "41:ba-c;41.2;b,a,-c;8;c2v^17;b b a 2;b 2 -2ab", "41:cab;41.3;c,a,b;8;c2v^17;b 2 e b;b -2ab 2", "41:cab;41.3;c,a,b;8;c2v^17;b 2 c b;b -2ab 2", "41:-cba;41.4;-c,b,a;8;c2v^17;c 2 c e;c -2ac 2", "41:-cba;41.4;-c,b,a;8;c2v^17;c 2 c b;c -2ac 2", "41:bca;41.5;b,c,a;8;c2v^17;c c 2 e;c -2ac -2ac", "41:bca;41.5;b,c,a;8;c2v^17;c c 2 a;c -2ac -2ac", "41:a-cb;41.6;a,-c,b;8;c2v^17;a e 2 a;a -2ab -2ab", "41:a-cb;41.6;a,-c,b;8;c2v^17;a c 2 a;a -2ab -2ab", "42;42.1;;16;c2v^18;f m m 2;f 2 -2", "42:cab;42.2;c,a,b;16;c2v^18;f 2 m m;f -2 2", "42:bca;42.3;b,c,a;16;c2v^18;f m 2 m;f -2 -2", "43;43.1;;16;c2v^19;f d d 2;f 2 -2d", "43:cab;43.2;c,a,b;16;c2v^19;f 2 d d;f -2d 2", "43:bca;43.3;b,c,a;16;c2v^19;f d 2 d;f -2d -2d", "44;44.1;;8;c2v^20;i m m 2;i 2 -2", "44:cab;44.2;c,a,b;8;c2v^20;i 2 m m;i -2 2", "44:bca;44.3;b,c,a;8;c2v^20;i m 2 m;i -2 -2", "45;45.1;;8;c2v^21;i b a 2;i 2 -2c", "45:cab;45.2;c,a,b;8;c2v^21;i 2 c b;i -2a 2", "45:bca;45.3;b,c,a;8;c2v^21;i c 2 a;i -2b -2b", "46;46.1;;8;c2v^22;i m a 2;i 2 -2a", "46:ba-c;46.2;b,a,-c;8;c2v^22;i b m 2;i 2 -2b", "46:cab;46.3;c,a,b;8;c2v^22;i 2 m b;i -2b 2", "46:-cba;46.4;-c,b,a;8;c2v^22;i 2 c m;i -2c 2", "46:bca;46.5;b,c,a;8;c2v^22;i c 2 m;i -2c -2c", "46:a-cb;46.6;a,-c,b;8;c2v^22;i m 2 a;i -2a -2a", "47;47.1;;8;d2h^1;p m m m;-p 2 2", "48:2;48.1;;8;d2h^2;p n n n :2;-p 2ab 2bc", "48:1;48.2;a,b,c|1/4,1/4,1/4;8;d2h^2;p n n n :1;p 2 2 -1n", "49;49.1;;8;d2h^3;p c c m;-p 2 2c", "49:cab;49.2;c,a,b;8;d2h^3;p m a a;-p 2a 2", "49:bca;49.3;b,c,a;8;d2h^3;p b m b;-p 2b 2b", "50:2;50.1;;8;d2h^4;p b a n :2;-p 2ab 2b", "50:2cab;50.2;c,a,b;8;d2h^4;p n c b :2;-p 2b 2bc", "50:2bca;50.3;b,c,a;8;d2h^4;p c n a :2;-p 2a 2c", "50:1;50.4;a,b,c|1/4,1/4,0;8;d2h^4;p b a n :1;p 2 2 -1ab", "50:1cab;50.5;c,a,b|1/4,1/4,0;8;d2h^4;p n c b :1;p 2 2 -1bc", "50:1bca;50.6;b,c,a|1/4,1/4,0;8;d2h^4;p c n a :1;p 2 2 -1ac", "51;51.1;;8;d2h^5;p m m a;-p 2a 2a", "51:ba-c;51.2;b,a,-c;8;d2h^5;p m m b;-p 2b 2", "51:cab;51.3;c,a,b;8;d2h^5;p b m m;-p 2 2b", "51:-cba;51.4;-c,b,a;8;d2h^5;p c m m;-p 2c 2c", "51:bca;51.5;b,c,a;8;d2h^5;p m c m;-p 2c 2", "51:a-cb;51.6;a,-c,b;8;d2h^5;p m a m;-p 2 2a", "52;52.1;;8;d2h^6;p n n a;-p 2a 2bc", "52:ba-c;52.2;b,a,-c;8;d2h^6;p n n b;-p 2b 2n", "52:cab;52.3;c,a,b;8;d2h^6;p b n n;-p 2n 2b", "52:-cba;52.4;-c,b,a;8;d2h^6;p c n n;-p 2ab 2c", "52:bca;52.5;b,c,a;8;d2h^6;p n c n;-p 2ab 2n", "52:a-cb;52.6;a,-c,b;8;d2h^6;p n a n;-p 2n 2bc", "53;53.1;;8;d2h^7;p m n a;-p 2ac 2", "53:ba-c;53.2;b,a,-c;8;d2h^7;p n m b;-p 2bc 2bc", "53:cab;53.3;c,a,b;8;d2h^7;p b m n;-p 2ab 2ab", "53:-cba;53.4;-c,b,a;8;d2h^7;p c n m;-p 2 2ac", "53:bca;53.5;b,c,a;8;d2h^7;p n c m;-p 2 2bc", "53:a-cb;53.6;a,-c,b;8;d2h^7;p m a n;-p 2ab 2", "54;54.1;;8;d2h^8;p c c a;-p 2a 2ac", "54:ba-c;54.2;b,a,-c;8;d2h^8;p c c b;-p 2b 2c", "54:cab;54.3;c,a,b;8;d2h^8;p b a a;-p 2a 2b", "54:-cba;54.4;-c,b,a;8;d2h^8;p c a a;-p 2ac 2c", "54:bca;54.5;b,c,a;8;d2h^8;p b c b;-p 2bc 2b", "54:a-cb;54.6;a,-c,b;8;d2h^8;p b a b;-p 2b 2ab", "55;55.1;;8;d2h^9;p b a m;-p 2 2ab", "55:cab;55.2;c,a,b;8;d2h^9;p m c b;-p 2bc 2", "55:bca;55.3;b,c,a;8;d2h^9;p c m a;-p 2ac 2ac", "56;56.1;;8;d2h^10;p c c n;-p 2ab 2ac", "56:cab;56.2;c,a,b;8;d2h^10;p n a a;-p 2ac 2bc", "56:bca;56.3;b,c,a;8;d2h^10;p b n b;-p 2bc 2ab", "57;57.1;;8;d2h^11;p b c m;-p 2c 2b", "57:ba-c;57.2;b,a,-c;8;d2h^11;p c a m;-p 2c 2ac", "57:cab;57.3;c,a,b;8;d2h^11;p m c a;-p 2ac 2a", "57:-cba;57.4;-c,b,a;8;d2h^11;p m a b;-p 2b 2a", "57:bca;57.5;b,c,a;8;d2h^11;p b m a;-p 2a 2ab", "57:a-cb;57.6;a,-c,b;8;d2h^11;p c m b;-p 2bc 2c", "58;58.1;;8;d2h^12;p n n m;-p 2 2n", "58:cab;58.2;c,a,b;8;d2h^12;p m n n;-p 2n 2", "58:bca;58.3;b,c,a;8;d2h^12;p n m n;-p 2n 2n", "59:2;59.1;;8;d2h^13;p m m n :2;-p 2ab 2a", "59:2cab;59.2;c,a,b;8;d2h^13;p n m m :2;-p 2c 2bc", "59:2bca;59.3;b,c,a;8;d2h^13;p m n m :2;-p 2c 2a", "59:1;59.4;a,b,c|1/4,1/4,0;8;d2h^13;p m m n :1;p 2 2ab -1ab", "59:1cab;59.5;c,a,b|1/4,1/4,0;8;d2h^13;p n m m :1;p 2bc 2 -1bc", "59:1bca;59.6;b,c,a|1/4,1/4,0;8;d2h^13;p m n m :1;p 2ac 2ac -1ac", "60;60.1;;8;d2h^14;p b c n;-p 2n 2ab", "60:ba-c;60.2;b,a,-c;8;d2h^14;p c a n;-p 2n 2c", "60:cab;60.3;c,a,b;8;d2h^14;p n c a;-p 2a 2n", "60:-cba;60.4;-c,b,a;8;d2h^14;p n a b;-p 2bc 2n", "60:bca;60.5;b,c,a;8;d2h^14;p b n a;-p 2ac 2b", "60:a-cb;60.6;a,-c,b;8;d2h^14;p c n b;-p 2b 2ac", "61;61.1;;8;d2h^15;p b c a;-p 2ac 2ab", "61:ba-c;61.2;b,a,-c;8;d2h^15;p c a b;-p 2bc 2ac", "62;62.1;;8;d2h^16;p n m a;-p 2ac 2n", "62:ba-c;62.2;b,a,-c;8;d2h^16;p m n b;-p 2bc 2a", "62:cab;62.3;c,a,b;8;d2h^16;p b n m;-p 2c 2ab", "62:-cba;62.4;-c,b,a;8;d2h^16;p c m n;-p 2n 2ac", "62:bca;62.5;b,c,a;8;d2h^16;p m c n;-p 2n 2a", "62:a-cb;62.6;a,-c,b;8;d2h^16;p n a m;-p 2c 2n", "63;63.1;;16;d2h^17;c m c m;-c 2c 2", "63:ba-c;63.2;b,a,-c;16;d2h^17;c c m m;-c 2c 2c", "63:cab;63.3;c,a,b;16;d2h^17;a m m a;-a 2a 2a", "63:-cba;63.4;-c,b,a;16;d2h^17;a m a m;-a 2 2a", "63:bca;63.5;b,c,a;16;d2h^17;b b m m;-b 2 2b", "63:a-cb;63.6;a,-c,b;16;d2h^17;b m m b;-b 2b 2", "64;64.1;;16;d2h^18;c m c e;-c 2ac 2", "64;64.1;;16;d2h^18;c m c a;-c 2ac 2", "64:ba-c;64.2;b,a,-c;16;d2h^18;c c m e;-c 2ac 2ac", "64:ba-c;64.2;b,a,-c;16;d2h^18;c c m b;-c 2ac 2ac", "64:cab;64.3;c,a,b;16;d2h^18;a e m a;-a 2ab 2ab", "64:cab;64.3;c,a,b;16;d2h^18;a b m a;-a 2ab 2ab", "64:-cba;64.4;-c,b,a;16;d2h^18;a e a m;-a 2 2ab", "64:-cba;64.4;-c,b,a;16;d2h^18;a c a m;-a 2 2ab", "64:bca;64.5;b,c,a;16;d2h^18;b b e m;-b 2 2ab", "64:bca;64.5;b,c,a;16;d2h^18;b b c m;-b 2 2ab", "64:a-cb;64.6;a,-c,b;16;d2h^18;b m e b;-b 2ab 2", "64:a-cb;64.6;a,-c,b;16;d2h^18;b m a b;-b 2ab 2", "65;65.1;;16;d2h^19;c m m m;-c 2 2", "65:cab;65.2;c,a,b;16;d2h^19;a m m m;-a 2 2", "65:bca;65.3;b,c,a;16;d2h^19;b m m m;-b 2 2", "66;66.1;;16;d2h^20;c c c m;-c 2 2c", "66:cab;66.2;c,a,b;16;d2h^20;a m a a;-a 2a 2", "66:bca;66.3;b,c,a;16;d2h^20;b b m b;-b 2b 2b", "67;67.1;;16;d2h^21;c m m e;-c 2a 2", "67;67.1;;16;d2h^21;c m m a;-c 2a 2", "67:ba-c;67.2;b,a,-c;16;d2h^21;c m m b;-c 2a 2a", "67:cab;67.3;c,a,b;16;d2h^21;a b m m;-a 2b 2b", "67:-cba;67.4;-c,b,a;16;d2h^21;a c m m;-a 2 2b", "67:bca;67.5;b,c,a;16;d2h^21;b m c m;-b 2 2a", "67:a-cb;67.6;a,-c,b;16;d2h^21;b m a m;-b 2a 2", "68:2;68.1;;16;d2h^22;c c c e :2;-c 2a 2ac", "68:2;68.1;;16;d2h^22;c c c a :2;-c 2a 2ac", "68:2ba-c;68.2;b,a,-c;16;d2h^22;c c c b :2;-c 2a 2c", "68:2cab;68.3;c,a,b;16;d2h^22;a b a a :2;-a 2a 2b", "68:2-cba;68.4;-c,b,a;16;d2h^22;a c a a :2;-a 2ab 2b", "68:2bca;68.5;b,c,a;16;d2h^22;b b c b :2;-b 2ab 2b", "68:2a-cb;68.6;a,-c,b;16;d2h^22;b b a b :2;-b 2b 2ab", "68:1;68.7;a,b,c|0,1/4,1/4;16;d2h^22;c c c e :1;c 2 2 -1ac", "68:1;68.7;a,b,c|0,1/4,1/4;16;d2h^22;c c c a :1;c 2 2 -1ac", "68:1ba-c;68.8;b,a,-c|0,1/4,1/4;16;d2h^22;c c c b :1;c 2 2 -1ac", "68:1cab;68.9;c,a,b|0,1/4,1/4;16;d2h^22;a b a a :1;a 2 2 -1ab", "68:1-cba;68.10;-c,b,a|0,1/4,1/4;16;d2h^22;a c a a :1;a 2 2 -1ab", "68:1bca;68.11;b,c,a|0,1/4,1/4;16;d2h^22;b b c b :1;b 2 2 -1ab", "68:1a-cb;68.12;a,-c,b|0,1/4,1/4;16;d2h^22;b b a b :1;b 2 2 -1ab", "69;69.1;;32;d2h^23;f m m m;-f 2 2", "70:2;70.1;;32;d2h^24;f d d d :2;-f 2uv 2vw", "70:1;70.2;a,b,c|-1/8,-1/8,-1/8;32;d2h^24;f d d d :1;f 2 2 -1d", "71;71.1;;16;d2h^25;i m m m;-i 2 2", "72;72.1;;16;d2h^26;i b a m;-i 2 2c", "72:cab;72.2;c,a,b;16;d2h^26;i m c b;-i 2a 2", "72:bca;72.3;b,c,a;16;d2h^26;i c m a;-i 2b 2b", "73;73.1;;16;d2h^27;i b c a;-i 2b 2c", "73:ba-c;73.2;b,a,-c;16;d2h^27;i c a b;-i 2a 2b", "74;74.1;;16;d2h^28;i m m a;-i 2b 2", "74:ba-c;74.2;b,a,-c;16;d2h^28;i m m b;-i 2a 2a", "74:cab;74.3;c,a,b;16;d2h^28;i b m m;-i 2c 2c", "74:-cba;74.4;-c,b,a;16;d2h^28;i c m m;-i 2 2b", "74:bca;74.5;b,c,a;16;d2h^28;i m c m;-i 2 2a", "74:a-cb;74.6;a,-c,b;16;d2h^28;i m a m;-i 2c 2", "75;75.1;;4;c4^1;p 4;p 4", "75:c;75.2;ab;8;c4^1;c 4;c 4", "76;76.1;;4;c4^2;p 41;p 4w", "76*;76.1;;4;c4^2;p 41*;p 41", "76:c;76.2;ab;8;c4^2;c 41;c 4w", "77;77.1;;4;c4^3;p 42;p 4c", "77*;77.1;;4;c4^3;p 42*;p 42", "77:c;77.2;ab;8;c4^3;c 42;c 4c", "78;78.1;;4;c4^4;p 43;p 4cw", "78*;78.1;;4;c4^4;p 43*;p 43", "78:c;78.2;ab;8;c4^4;c 43;c 4cw", "79;79.1;;8;c4^5;i 4;i 4", "79:f;79.2;ab;16;c4^5;f 4;f 4", "80;80.1;;8;c4^6;i 41;i 4bw", "80:f;80.2;ab;16;c4^6;f 41;xyz", "81;81.1;;4;s4^1;p -4;p -4", "81:c;81.2;ab;8;s4^1;c -4;c -4", "82;82.1;;8;s4^2;i -4;i -4", "82:f;82.2;ab;16;s4^2;f -4;f -4", "83;83.1;;8;c4h^1;p 4/m;-p 4", "83:f;83.2;ab;16;c4h^1;c 4/m;-c 4", "84;84.1;;8;c4h^2;p 42/m;-p 4c", "84*;84.1;;8;c4h^2;p 42/m*;-p 42", "84:c;84.2;ab;16;c4h^2;c 42/m;-c 4c", "85:2;85.1;;8;c4h^3;p 4/n :2;-p 4a", "85:c2;85.2;ab;16;c4h^3;c 4/e :2;xyz", "85:1;85.3;a,b,c|-1/4,1/4,0;8;c4h^3;p 4/n :1;p 4ab -1ab", "85:c1;85.4;ab|-1/4,1/4,0;16;c4h^3;c 4/e :1;xyz", "86:2;86.1;;8;c4h^4;p 42/n :2;-p 4bc", "86:1;86.3;a,b,c|-1/4,-1/4,-1/4;8;c4h^4;p 42/n :1;p 4n -1n", "86:c1;86.4;ab|-1/4,-1/4,-1/4;16;c4h^4;c 42/e :1;xyz", "86:c2;86.2;ab;16;c4h^4;c 42/e :2;xyz", "87;87.1;;16;c4h^5;i 4/m;-i 4", "87:f;87.2;ab;32;c4h^5;f 4/m;xyz", "88:2;88.1;;16;c4h^6;i 41/a :2;-i 4ad", "88:f2;88.2;ab;32;c4h^6;f 41/d :2;xyz", "88:1;88.3;a,b,c|0,-1/4,-1/8;16;c4h^6;i 41/a :1;i 4bw -1bw", "88:f1;88.4;ab|0,-1/4,-1/8;32;c4h^6;f 41/d :1;xyz", "89;89.1;;8;d4^1;p 4 2 2;p 4 2", "89:c;89.2;ab;16;d4^1;c 4 2 2;xyz", "90;90.1;;8;d4^2;p 4 21 2;p 4ab 2ab", "90:c;90.2;ab;16;d4^2;c 4 2 21;xyz", "91;91.1;;8;d4^3;p 41 2 2;p 4w 2c", "91*;91.1;;8;d4^3;p 41 2 2*;p 41 2c", "91:c;91.2;ab;16;d4^3;c 41 2 2;xyz", "92;92.1;;8;d4^4;p 41 21 2;p 4abw 2nw", "92:c;92.2;ab;16;d4^4;c 41 2 21;xyz", "93;93.1;;8;d4^5;p 42 2 2;p 4c 2", "93*;93.1;;8;d4^5;p 42 2 2*;p 42 2", "93:c;93.2;ab;16;d4^5;c 42 2 2;xyz", "94;94.1;;8;d4^6;p 42 21 2;p 4n 2n", "94:c;94.2;ab;16;d4^6;c 42 2 21;xyz", "95;95.1;;8;d4^7;p 43 2 2;p 4cw 2c", "95*;95.1;;8;d4^7;p 43 2 2*;p 43 2c", "95:c;95.2;ab;16;d4^7;c 43 2 2;xyz", "96;96.1;;8;d4^8;p 43 21 2;p 4nw 2abw", "96:c;96.2;ab;16;d4^8;c 43 2 21;xyz", "97;97.1;;16;d4^9;i 4 2 2;i 4 2", "97:f;97.2;ab;32;d4^9;f 4 2 2;f 4 2", "98;98.1;;16;d4^10;i 41 2 2;i 4bw 2bw", "98:f;98.2;ab;32;d4^10;f 41 2 2;xyz", "99;99.1;;8;c4v^1;p 4 m m;p 4 -2", "99:c;99.2;ab;16;c4v^1;c 4 m m;c 4 -2", "100;100.1;;8;c4v^2;p 4 b m;p 4 -2ab", "100:c;100.2;ab;16;c4v^2;c 4 m g1;xyz", "101;101.1;;8;c4v^3;p 42 c m;p 4c -2c", "101*;101.1;;8;c4v^3;p 42 c m*;p 42 -2c", "101:c;101.2;ab;16;c4v^3;c 42 m c;xyz", "102;102.1;;8;c4v^4;p 42 n m;p 4n -2n", "102:c;102.2;ab;16;c4v^4;c 42 m g2;xyz", "103;103.1;;8;c4v^5;p 4 c c;p 4 -2c", "103:c;103.2;ab;16;c4v^5;c 4 c c;c 4 -2c", "104;104.1;;8;c4v^6;p 4 n c;p 4 -2n", "104:c;104.2;ab;16;c4v^6;c 4 c g2;xyz", "105;105.1;;8;c4v^7;p 42 m c;p 4c -2", "105*;105.1;;8;c4v^7;p 42 m c*;p 42 -2", "105:c;105.2;ab;16;c4v^7;c 42 c m;xyz", "106;106.1;;8;c4v^8;p 42 b c;p 4c -2ab", "106*;106.1;;8;c4v^8;p 42 b c*;p 42 -2ab", "106:c;106.2;ab;16;c4v^8;c 42 c g1;xyz", "107;107.1;;16;c4v^9;i 4 m m;i 4 -2", "107:f;107.2;ab;32;c4v^9;f 4 m m;f 4 -2", "108;108.1;;16;c4v^10;i 4 c m;i 4 -2c", "108:f;108.2;ab;32;c4v^10;f 4 m c;xyz", "109;109.1;;16;c4v^11;i 41 m d;i 4bw -2", "109:f;109.2;ab;32;c4v^11;f 41 d m;xyz", "110;110.1;;16;c4v^12;i 41 c d;i 4bw -2c", "110:f;110.2;ab;32;c4v^12;f 41 d c;xyz", "111;111.1;;8;d2d^1;p -4 2 m;p -4 2", "111:c;111.2;ab;16;d2d^1;c -4 m 2;xyz", "112;112.1;;8;d2d^2;p -4 2 c;p -4 2c", "112:c;112.2;ab;16;d2d^2;c -4 c 2;xyz", "113;113.1;;8;d2d^3;p -4 21 m;p -4 2ab", "113:c;113.2;ab;16;d2d^3;c -4 m 21;xyz", "114;114.1;;8;d2d^4;p -4 21 c;p -4 2n", "114:c;114.2;ab;16;d2d^4;c -4 c 21;xyz", "115;115.1;;8;d2d^5;p -4 m 2;p -4 -2", "115:c;115.2;ab;16;d2d^5;c -4 2 m;xyz", "116;116.1;;8;d2d^6;p -4 c 2;p -4 -2c", "116:c;116.2;ab;16;d2d^6;c -4 2 c;xyz", "117;117.1;;8;d2d^7;p -4 b 2;p -4 -2ab", "117:c;117.2;ab;16;d2d^7;c -4 2 g1;xyz", "118;118.1;;8;d2d^8;p -4 n 2;p -4 -2n", "118:c;118.2;ab;16;d2d^8;c -4 2 g2;xyz", "119;119.1;;16;d2d^9;i -4 m 2;i -4 -2", "119:f;119.2;ab;32;d2d^9;f -4 2 m;xyz", "120;120.1;;16;d2d^10;i -4 c 2;i -4 -2c", "120:f;120.2;ab;32;d2d^10;f -4 2 c;xyz", "121;121.1;;16;d2d^11;i -4 2 m;i -4 2", "121:f;121.2;ab;32;d2d^11;f -4 m 2;xyz", "122;122.1;;16;d2d^12;i -4 2 d;i -4 2bw", "122:f;122.2;ab;32;d2d^12;f -4 d 2;xyz", "123;123.1;;16;d4h^1;p 4/m m m;-p 4 2", "123:c;123.2;ab;32;d4h^1;c 4/m m m;xyz", "124;124.1;;16;d4h^2;p 4/m c c;-p 4 2c", "124:c;124.2;ab;32;d4h^2;c 4/m c c;xyz", "125:2;125.1;;16;d4h^3;p 4/n b m :2;-p 4a 2b", "125:c2;125.2;ab;32;d4h^3;c 4/e m g1 :2;xyz", "125:1;125.3;a,b,c|-1/4,-1/4,0;16;d4h^3;p 4/n b m :1;p 4 2 -1ab", "125:c1;125.4;ab|-1/4,-1/4,0;32;d4h^3;c 4/e m g1 :1;xyz", "126:2;126.1;;16;d4h^4;p 4/n n c :2;-p 4a 2bc", "126:c1;126.2;ab;32;d4h^4;c 4/e c g2 :2;xyz", "126:1;126.3;a,b,c|-1/4,-1/4,-1/4;16;d4h^4;p 4/n n c :1;p 4 2 -1n", "126:c4;126.4;ab|-1/4,-1/4,-1/4;32;d4h^4;c 4/e c g2 :1;xyz", "127;127.1;;16;d4h^5;p 4/m b m;-p 4 2ab", "127:c;127.2;ab;32;d4h^5;c 4/m m g1;xyz", "128;128.1;;16;d4h^6;p 4/m n c;-p 4 2n", "128:c;128.2;a+b,-a+b,c;32;d4h^6;c 4/m c g2;xyz", "129:2;129.1;;16;d4h^7;p 4/n m m :2;-p 4a 2a", "129:c2;129.2;ab;32;d4h^7;c 4/e m m :2;xyz", "129:1;129.3;a,b,c|-1/4,1/4,0;16;d4h^7;p 4/n m m :1;p 4ab 2ab -1ab", "129:c1;129.4;ab|-1/4,1/4,0;32;d4h^7;c 4/e m m :1;xyz", "130:2;130.1;;16;d4h^8;p 4/n c c :2;-p 4a 2ac", "130:c2;130.2;ab;32;d4h^8;c 4/e c c :2;xyz", "130:1;130.3;a,b,c|-1/4,1/4,0;16;d4h^8;p 4/n c c :1;p 4ab 2n -1ab", "130:c1;130.4;ab|-1/4,1/4,0;32;d4h^8;c 4/e c c :1;xyz", "131;131.1;;16;d4h^9;p 42/m m c;-p 4c 2", "131:c;131.2;ab;32;d4h^9;c 42/m c m;xyz", "132;132.1;;16;d4h^10;p 42/m c m;-p 4c 2c", "132:c;132.2;ab;32;d4h^10;c 42/m m c;xyz", "133:2;133.1;;16;d4h^11;p 42/n b c :2;-p 4ac 2b", "133:c1;133.2;ab;32;d4h^11;c 42/e c g1 :2;xyz", "133:1;133.3;a,b,c|-1/4,1/4,-1/4;16;d4h^11;p 42/n b c :1;p 4n 2c -1n", "133:c2;133.4;ab|-1/4,1/4,-1/4;32;d4h^11;c 42/e c g1 :1;xyz", "134:2;134.1;;16;d4h^12;p 42/n n m :2;-p 4ac 2bc", "134:c2;134.2;ab;32;d4h^12;c 42/e m g2 :2;xyz", "134:1;134.3;a,b,c|-1/4,1/4,-1/4;16;d4h^12;p 42/n n m :1;p 4n 2 -1n", "134:c1;134.4;ab|-1/4,1/4,-1/4;32;d4h^12;c 42/e m g2 :1;xyz", "135;135.1;;16;d4h^13;p 42/m b c;-p 4c 2ab", "135*;135.1;;16;d4h^13;p 42/m b c*;-p 42 2ab", "135:c;135.2;ab;32;d4h^13;c 42/m c g1;xyz", "136;136.1;;16;d4h^14;p 42/m n m;-p 4n 2n", "136:c;136.2;ab;32;d4h^14;c 42/m m g2;xyz", "137:2;137.1;;16;d4h^15;p 42/n m c :2;-p 4ac 2a", "137:c1;137.2;ab;32;d4h^15;c 42/e c m :2;xyz", "137:1;137.3;a,b,c|-1/4,1/4,-1/4;16;d4h^15;p 42/n m c :1;p 4n 2n -1n", "137:c2;137.4;ab|-1/4,1/4,-1/4;32;d4h^15;c 42/e c m :1;xyz", "138:2;138.1;;16;d4h^16;p 42/n c m :2;-p 4ac 2ac", "138:c2;138.2;ab;32;d4h^16;c 42/e m c :2;xyz", "138:1;138.3;a,b,c|-1/4,1/4,-1/4;16;d4h^16;p 42/n c m :1;p 4n 2ab -1n", "138:c1;138.4;ab|-1/4,1/4,-1/4;32;d4h^16;c 42/e m c :1;xyz", "139;139.1;;32;d4h^17;i 4/m m m;-i 4 2", "139:f;139.2;ab;64;d4h^17;f 4/m m m;xyz", "140;140.1;;32;d4h^18;i 4/m c m;-i 4 2c", "140:f;140.2;ab;64;d4h^18;f 4/m m c;xyz", "141:2;141.1;;32;d4h^19;i 41/a m d :2;-i 4bd 2", "141:f2;141.2;ab;64;d4h^19;f 41/d d m :2;xyz", "141:1;141.3;a,b,c|0,1/4,-1/8;32;d4h^19;i 41/a m d :1;i 4bw 2bw -1bw", "141:f1;141.4;ab|0,1/4,-1/8;64;d4h^19;f 41/d d m :1;xyz", "142:2;142.1;;32;d4h^20;i 41/a c d :2;-i 4bd 2c", "142:f2;142.2;ab;64;d4h^20;f 41/d d c :2;xyz", "142:1;142.3;a,b,c|0,1/4,-1/8;32;d4h^20;i 41/a c d :1;i 4bw 2aw -1bw", "142:f1;142.4;ab|0,1/4,-1/8;64;d4h^20;f 41/d d c :1;xyz", "143;143.1;;3;c3^1;p 3;p 3", "144;144.1;;3;c3^2;p 31;p 31", "145;145.1;;3;c3^3;p 32;p 32", "146:h;146.1;;9;c3^4;r 3 :h;r 3", "146:r;146.2;r;3;c3^4;r 3 :r;p 3*", "147;147.1;;6;c3i^1;p -3;-p 3", "148:h;148.1;;18;c3i^2;r -3 :h;-r 3", "148:r;148.2;r;6;c3i^2;r -3 :r;-p 3*", "149;149.1;;6;d3^1;p 3 1 2;p 3 2", "150;150.1;;6;d3^2;p 3 2 1;p 3 2\"", "151;151.1;;6;d3^3;p 31 1 2;p 31 2 (0 0 4)", "152;152.1;;6;d3^4;p 31 2 1;p 31 2\"", "152:_2;152:a,b,c|0,0,-1/3;a,b,c|0,0,-1/3;6;d3^4;p 31 2 1;p 31 2\" (0 0 -4)", "153;153.1;;6;d3^5;p 32 1 2;p 32 2 (0 0 2)", "154;154.1;;6;d3^6;p 32 2 1;p 32 2\"", "154:_2;154:a,b,c|0,0,-1/3;a,b,c|0,0,-1/3;6;d3^6;p 32 2 1;p 32 2\" (0 0 4)", "155:h;155.1;;18;d3^7;r 3 2 :h;r 3 2\"", "155:r;155.2;r;6;d3^7;r 3 2 :r;p 3* 2", "156;156.1;;6;c3v^1;p 3 m 1;p 3 -2\"", "157;157.1;;6;c3v^2;p 3 1 m;p 3 -2", "158;158.1;;6;c3v^3;p 3 c 1;p 3 -2\"c", "159;159.1;;6;c3v^4;p 3 1 c;p 3 -2c", "160:h;160.1;;18;c3v^5;r 3 m :h;r 3 -2\"", "160:r;160.2;r;6;c3v^5;r 3 m :r;p 3* -2", "161:h;161.1;;18;c3v^6;r 3 c :h;r 3 -2\"c", "161:r;161.2;r;6;c3v^6;r 3 c :r;p 3* -2n", "162;162.1;;12;d3d^1;p -3 1 m;-p 3 2", "163;163.1;;12;d3d^2;p -3 1 c;-p 3 2c", "164;164.1;;12;d3d^3;p -3 m 1;-p 3 2\"", "165;165.1;;12;d3d^4;p -3 c 1;-p 3 2\"c", "166:h;166.1;;36;d3d^5;r -3 m :h;-r 3 2\"", "166:r;166.2;r;12;d3d^5;r -3 m :r;-p 3* 2", "167:h;167.1;;36;d3d^6;r -3 c :h;-r 3 2\"c", "167:r;167.2;r;12;d3d^6;r -3 c :r;-p 3* 2n", "168;168.1;;6;c6^1;p 6;p 6", "169;169.1;;6;c6^2;p 61;p 61", "170;170.1;;6;c6^3;p 65;p 65", "171;171.1;;6;c6^4;p 62;p 62", "172;172.1;;6;c6^5;p 64;p 64", "173;173.1;;6;c6^6;p 63;p 6c", "173*;173.1;;6;c6^6;p 63*;p 63 ", "174;174.1;;6;c3h^1;p -6;p -6", "175;175.1;;12;c6h^1;p 6/m;-p 6", "176;176.1;;12;c6h^2;p 63/m;-p 6c", "176*;176.1;;12;c6h^2;p 63/m*;-p 63", "177;177.1;;12;d6^1;p 6 2 2;p 6 2", "178;178.1;;12;d6^2;p 61 2 2;p 61 2 (0 0 5)", "179;179.1;;12;d6^3;p 65 2 2;p 65 2 (0 0 1)", "180;180.1;;12;d6^4;p 62 2 2;p 62 2 (0 0 4)", "181;181.1;;12;d6^5;p 64 2 2;p 64 2 (0 0 2)", "182;182.1;;12;d6^6;p 63 2 2;p 6c 2c", "182*;182.1;;12;d6^6;p 63 2 2*;p 63 2c", "183;183.1;;12;c6v^1;p 6 m m;p 6 -2", "184;184.1;;12;c6v^2;p 6 c c;p 6 -2c", "185;185.1;;12;c6v^3;p 63 c m;p 6c -2", "185*;185.1;;12;c6v^3;p 63 c m*;p 63 -2", "186;186.1;;12;c6v^4;p 63 m c;p 6c -2c", "186*;186.1;;12;c6v^4;p 63 m c*;p 63 -2c", "187;187.1;;12;d3h^1;p -6 m 2;p -6 2", "188;188.1;;12;d3h^2;p -6 c 2;p -6c 2", "189;189.1;;12;d3h^3;p -6 2 m;p -6 -2", "190;190.1;;12;d3h^4;p -6 2 c;p -6c -2c", "191;191.1;;24;d6h^1;p 6/m m m;-p 6 2", "192;192.1;;24;d6h^2;p 6/m c c;-p 6 2c", "193;193.1;;24;d6h^3;p 63/m c m;-p 6c 2", "193*;193.1;;24;d6h^3;p 63/m c m*;-p 63 2", "194;194.1;;24;d6h^4;p 63/m m c;-p 6c 2c", "194*;194.1;;24;d6h^4;p 63/m m c*;-p 63 2c", "195;195.1;;12;t^1;p 2 3;p 2 2 3", "196;196.1;;48;t^2;f 2 3;f 2 2 3", "197;197.1;;24;t^3;i 2 3;i 2 2 3", "198;198.1;;12;t^4;p 21 3;p 2ac 2ab 3", "199;199.1;;24;t^5;i 21 3;i 2b 2c 3", "200;200.1;;24;th^1;p m -3;-p 2 2 3", "201:2;201.1;;24;th^2;p n -3 :2;-p 2ab 2bc 3", "201:1;201.2;a,b,c|-1/4,-1/4,-1/4;24;th^2;p n -3 :1;p 2 2 3 -1n", "202;202.1;;96;th^3;f m -3;-f 2 2 3", "203:2;203.1;;96;th^4;f d -3 :2;-f 2uv 2vw 3", "203:1;203.2;a,b,c|-1/8,-1/8,-1/8;96;th^4;f d -3 :1;f 2 2 3 -1d", "204;204.1;;48;th^5;i m -3;-i 2 2 3", "205;205.1;;24;th^6;p a -3;-p 2ac 2ab 3", "206;206.1;;48;th^7;i a -3;-i 2b 2c 3", "207;207.1;;24;o^1;p 4 3 2;p 4 2 3", "208;208.1;;24;o^2;p 42 3 2;p 4n 2 3", "209;209.1;;96;o^3;f 4 3 2;f 4 2 3", "210;210.1;;96;o^4;f 41 3 2;f 4d 2 3", "211;211.1;;48;o^5;i 4 3 2;i 4 2 3", "212;212.1;;24;o^6;p 43 3 2;p 4acd 2ab 3", "213;213.1;;24;o^7;p 41 3 2;p 4bd 2ab 3", "214;214.1;;48;o^8;i 41 3 2;i 4bd 2c 3", "215;215.1;;24;td^1;p -4 3 m;p -4 2 3", "216;216.1;;96;td^2;f -4 3 m;f -4 2 3", "217;217.1;;48;td^3;i -4 3 m;i -4 2 3", "218;218.1;;24;td^4;p -4 3 n;p -4n 2 3", "219;219.1;;96;td^5;f -4 3 c;f -4a 2 3", "220;220.1;;48;td^6;i -4 3 d;i -4bd 2c 3", "221;221.1;;48;oh^1;p m -3 m;-p 4 2 3", "222:2;222.1;;48;oh^2;p n -3 n :2;-p 4a 2bc 3", "222:1;222.2;a,b,c|-1/4,-1/4,-1/4;48;oh^2;p n -3 n :1;p 4 2 3 -1n", "223;223.1;;48;oh^3;p m -3 n;-p 4n 2 3", "224:2;224.1;;48;oh^4;p n -3 m :2;-p 4bc 2bc 3", "224:1;224.2;a,b,c|-1/4,-1/4,-1/4;48;oh^4;p n -3 m :1;p 4n 2 3 -1n", "225;225.1;;192;oh^5;f m -3 m;-f 4 2 3", "226;226.1;;192;oh^6;f m -3 c;-f 4a 2 3", "227:2;227.1;;192;oh^7;f d -3 m :2;-f 4vw 2vw 3", "227:1;227.2;a,b,c|-1/8,-1/8,-1/8;192;oh^7;f d -3 m :1;f 4d 2 3 -1d", "228:2;228.1;;192;oh^8;f d -3 c :2;-f 4ud 2vw 3", "228:1;228.2;a,b,c|-3/8,-3/8,-3/8;192;oh^8;f d -3 c :1;f 4d 2 3 -1ad", "229;229.1;;96;oh^9;i m -3 m;-i 4 2 3", "230;230.1;;96;oh^10;i a -3 d;-i 4bd 2c 3"]);
{
JS.SpaceGroup.getSpaceGroups();
}});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024

Clazz.declarePackage("JM");
Clazz.load(null, "JM.BioExt", ["java.util.Hashtable", "JU.AU", "$.BS", "$.Lst", "$.P3", "$.PT", "$.Quat", "JM.LabelToken", "JU.BSUtil", "$.Escape", "$.Logger", "JV.Viewer"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.vwr = null;
this.ms = null;
Clazz.instantialize(this, arguments);}, JM, "BioExt", null);
/*LV!1824 unnec constructor*/Clazz.defineMethod(c$, "set", 
function(vwr, ms){
this.vwr = vwr;
this.ms = ms;
return this;
}, "JV.Viewer,JM.ModelSet");
Clazz.defineMethod(c$, "getAllPolymerInfo", 
function(bs, fullInfo){
var modelVector =  new JU.Lst();
var modelCount = this.ms.mc;
var models = this.ms.am;
for (var i = 0; i < modelCount; ++i) if (models[i].isBioModel) {
var m = models[i];
var modelInfo =  new java.util.Hashtable();
var info =  new JU.Lst();
for (var ip = 0; ip < m.bioPolymerCount; ip++) {
var bp = m.bioPolymers[ip];
var pInfo =  new java.util.Hashtable();
var mInfo =  new JU.Lst();
var sInfo = null;
var ps;
var psLast = null;
var n = 0;
var ptTemp =  new JU.P3();
for (var im = 0; im < bp.monomerCount; im++) {
if (bs.get(bp.monomers[im].leadAtomIndex)) {
var monomerInfo = bp.monomers[im].getMyInfo(ptTemp);
monomerInfo.put("monomerIndex", Integer.$valueOf(im));
mInfo.addLast(monomerInfo);
if ((ps = bp.getProteinStructure(im)) != null && ps !== psLast) {
var psInfo =  new java.util.Hashtable();
psLast = ps;
psInfo.put("type", ps.type.getBioStructureTypeName(false));
var leadAtomIndices = bp.getLeadAtomIndices();
var iArray = JU.AU.arrayCopyRangeI(leadAtomIndices, ps.monomerIndexFirst, ps.monomerIndexFirst + ps.nRes);
psInfo.put("leadAtomIndices", iArray);
ps.calcAxis();
if (ps.axisA != null) {
psInfo.put("axisA", ps.axisA);
psInfo.put("axisB", ps.axisB);
psInfo.put("axisUnitVector", ps.axisUnitVector);
}psInfo.put("index", Integer.$valueOf(n++));
if (sInfo == null) sInfo =  new JU.Lst();
sInfo.addLast(psInfo);
}}}
if (mInfo.size() > 0) {
pInfo.put("sequence", bp.getSequence());
pInfo.put("monomers", mInfo);
if (sInfo != null) pInfo.put("structures", sInfo);
}if (!pInfo.isEmpty()) info.addLast(pInfo);
}
if (info.size() > 0) {
modelInfo.put("modelIndex", Integer.$valueOf(m.modelIndex));
modelInfo.put("polymers", info);
modelVector.addLast(modelInfo);
}}
fullInfo.put("models", modelVector);
}, "JU.BS,java.util.Map");
Clazz.defineMethod(c$, "calculateStraightnessAll", 
function(){
var qtype = this.vwr.getQuaternionFrame();
var mStep = this.vwr.getInt(553648142);
for (var i = this.ms.mc; --i >= 0; ) if (this.ms.am[i].isBioModel) {
var m = this.ms.am[i];
var ptTemp =  new JU.P3();
for (var p = 0; p < m.bioPolymerCount; p++) this.getPdbData(m.bioPolymers[p], 'S', qtype, mStep, 2, null, null, false, false, false, null, null, null,  new JU.BS(), ptTemp);

}
this.ms.haveStraightness = true;
});
Clazz.defineMethod(c$, "getPdbData", 
function(bp, ctype, qtype, mStep, derivType, bsAtoms, bsSelected, bothEnds, isDraw, addHeader, tokens, pdbATOM, pdbCONECT, bsWritten, ptTemp){
var calcRamachandranStraightness = (qtype == 'C' || qtype == 'P');
var isRamachandran = (ctype == 'R' || ctype == 'S' && calcRamachandranStraightness);
if (isRamachandran && !bp.calcPhiPsiAngles()) return;
var isAmino = (bp.type == 1);
var isRelativeAlias = (ctype == 'r');
var quaternionStraightness = (!isRamachandran && ctype == 'S');
if (derivType == 2 && isRelativeAlias) ctype = 'w';
if (quaternionStraightness) derivType = 2;
var useQuaternionStraightness = (ctype == 'S');
var writeRamachandranStraightness = ("rcpCP".indexOf(qtype) >= 0);
if (JU.Logger.debugging && (quaternionStraightness || calcRamachandranStraightness)) {
JU.Logger.debug("For straightness calculation: useQuaternionStraightness = " + useQuaternionStraightness + " and quaternionFrame = " + qtype);
}if (addHeader && !isDraw) {
pdbATOM.append("REMARK   6    AT GRP CH RESNO  ");
switch ((ctype).charCodeAt(0)) {
default:
case 119:
pdbATOM.append("x*10___ y*10___ z*10___      w*10__       ");
break;
case 120:
pdbATOM.append("y*10___ z*10___ w*10___      x*10__       ");
break;
case 121:
pdbATOM.append("z*10___ w*10___ x*10___      y*10__       ");
break;
case 122:
pdbATOM.append("w*10___ x*10___ y*10___      z*10__       ");
break;
case 82:
if (writeRamachandranStraightness) pdbATOM.append("phi____ psi____ theta         Straightness");
 else pdbATOM.append("phi____ psi____ omega-180    PartialCharge");
break;
}
pdbATOM.append("    Sym   q0_______ q1_______ q2_______ q3_______");
pdbATOM.append("  theta_  aaX_______ aaY_______ aaZ_______");
if (ctype != 'R') pdbATOM.append("  centerX___ centerY___ centerZ___");
if (qtype == 'n') pdbATOM.append("  NHX_______ NHY_______ NHZ_______");
pdbATOM.append("\n\n");
}var factor = (ctype == 'R' ? 1 : 10);
bothEnds = false;
for (var j = 0; j < (bothEnds ? 2 : 1); j++, factor *= -1) for (var i = 0; i < (mStep < 1 ? 1 : mStep); i++) if (bp.hasStructure) this.getData(i, mStep, bp, ctype, qtype, derivType, bsAtoms, bsSelected, isDraw, isRamachandran, calcRamachandranStraightness, useQuaternionStraightness, writeRamachandranStraightness, quaternionStraightness, factor, isAmino, isRelativeAlias, tokens, pdbATOM, pdbCONECT, bsWritten, ptTemp);


}, "JM.BioPolymer,~S,~S,~N,~N,JU.BS,JU.BS,~B,~B,~B,~A,JU.OC,JU.SB,JU.BS,JU.P3");
Clazz.defineMethod(c$, "getData", 
function(m0, mStep, p, ctype, qtype, derivType, bsAtoms, bsSelected, isDraw, isRamachandran, calcRamachandranStraightness, useQuaternionStraightness, writeRamachandranStraightness, quaternionStraightness, factor, isAmino, isRelativeAlias, tokens, pdbATOM, pdbCONECT, bsWritten, ptTemp){
var prefix = (derivType > 0 ? "dq" + (derivType == 2 ? "2" : "") : "q");
var q;
var aprev = null;
var qprev = null;
var dq = null;
var dqprev = null;
var qref = null;
var atomLast = null;
var x = 0;
var y = 0;
var z = 0;
var w = 0;
var strExtra = "";
var val1 = NaN;
var val2 = NaN;
var pt = (isDraw ?  new JU.P3() : null);
var dm = (mStep <= 1 ? 1 : mStep);
for (var m = m0; m < p.monomerCount; m += dm) {
var monomer = p.monomers[m];
if (bsAtoms == null || bsAtoms.get(monomer.leadAtomIndex)) {
var a = monomer.getLeadAtom();
var id = monomer.getUniqueID();
if (isRamachandran) {
if (ctype == 'S') monomer.setGroupParameter(1111490574, NaN);
x = monomer.getGroupParameter(1111490569);
y = monomer.getGroupParameter(1111490570);
z = monomer.getGroupParameter(1111490568);
if (z < -90) z += 360;
z -= 180;
if (Float.isNaN(x) || Float.isNaN(y) || Float.isNaN(z)) {
if (bsAtoms != null) bsAtoms.clear(a.i);
continue;
}var angledeg = (writeRamachandranStraightness ? p.calculateRamachandranHelixAngle(m, qtype) : 0);
var straightness = (calcRamachandranStraightness || writeRamachandranStraightness ? JM.BioExt.getStraightness(Math.cos(angledeg / 2 / 180 * 3.141592653589793)) : 0);
if (ctype == 'S') {
monomer.setGroupParameter(1111490574, straightness);
continue;
}if (isDraw) {
if (bsSelected != null && !bsSelected.get(a.getIndex())) continue;
var aa = monomer;
pt.set(-x, x, 0.5);
pdbATOM.append("draw ID \"phi").append(id).append("\" ARROW ARC ").append(JU.Escape.eP(aa.getNitrogenAtom())).append(JU.Escape.eP(a)).append(JU.Escape.eP(aa.getCarbonylCarbonAtom())).append(JU.Escape.eP(pt)).append(" \"phi = ").append(String.valueOf(Math.round(x))).append("\" color ").append(JM.BioExt.qColor[2]).append("\n");
pt.set(0, y, 0.5);
pdbATOM.append("draw ID \"psi").append(id).append("\" ARROW ARC ").append(JU.Escape.eP(a)).append(JU.Escape.eP(aa.getCarbonylCarbonAtom())).append(JU.Escape.eP(aa.getNitrogenAtom())).append(JU.Escape.eP(pt)).append(" \"psi = ").append(String.valueOf(Math.round(y))).append("\" color ").append(JM.BioExt.qColor[1]).append("\n");
pdbATOM.append("draw ID \"planeNCC").append(id).append("\" ").append(JU.Escape.eP(aa.getNitrogenAtom())).append(JU.Escape.eP(a)).append(JU.Escape.eP(aa.getCarbonylCarbonAtom())).append(" color ").append(JM.BioExt.qColor[0]).append("\n");
pdbATOM.append("draw ID \"planeCNC").append(id).append("\" ").append(JU.Escape.eP((p.monomers[m - 1]).getCarbonylCarbonAtom())).append(JU.Escape.eP(aa.getNitrogenAtom())).append(JU.Escape.eP(a)).append(" color ").append(JM.BioExt.qColor[1]).append("\n");
pdbATOM.append("draw ID \"planeCCN").append(id).append("\" ").append(JU.Escape.eP(a)).append(JU.Escape.eP(aa.getCarbonylCarbonAtom())).append(JU.Escape.eP((p.monomers[m + 1]).getNitrogenAtom())).append(" color ").append(JM.BioExt.qColor[2]).append("\n");
continue;
}if (Float.isNaN(angledeg)) {
strExtra = "";
if (writeRamachandranStraightness) continue;
} else {
q = JU.Quat.newVA(JU.P3.new3(1, 0, 0), angledeg);
strExtra = JM.BioExt.getQInfo(q);
if (writeRamachandranStraightness) {
z = angledeg;
w = straightness;
} else {
w = a.getPartialCharge();
}}} else {
q = monomer.getQuaternion(qtype);
if (q != null) {
q.setRef(qref);
qref = JU.Quat.newQ(q);
}if (derivType == 2) monomer.setGroupParameter(1111490574, NaN);
if (q == null) {
qprev = null;
qref = null;
} else if (derivType > 0) {
var anext = a;
var qnext = q;
if (qprev == null) {
q = null;
dqprev = null;
} else {
if (isRelativeAlias) {
dq = qprev.leftDifference(q);
} else {
dq = q.rightDifference(qprev);
}if (derivType == 1) {
q = dq;
} else if (dqprev == null) {
q = null;
} else {
q = dq.rightDifference(dqprev);
val1 = JM.BioExt.getQuaternionStraightness(id, dqprev, dq);
val2 = JM.BioExt.get3DStraightness(id, dqprev, dq);
(aprev.group).setGroupParameter(1111490574, useQuaternionStraightness ? val1 : val2);
}dqprev = dq;
}aprev = anext;
qprev = qnext;
}if (q == null) {
atomLast = null;
continue;
}switch ((ctype).charCodeAt(0)) {
default:
x = q.q1;
y = q.q2;
z = q.q3;
w = q.q0;
break;
case 120:
x = q.q0;
y = q.q1;
z = q.q2;
w = q.q3;
break;
case 121:
x = q.q3;
y = q.q0;
z = q.q1;
w = q.q2;
break;
case 122:
x = q.q2;
y = q.q3;
z = q.q0;
w = q.q1;
break;
}
var ptCenter = monomer.getQuaternionFrameCenter(qtype);
if (ptCenter == null) ptCenter =  new JU.P3();
if (isDraw) {
if (bsSelected != null && !bsSelected.get(a.getIndex())) continue;
var deg = Clazz.doubleToInt(Math.floor(Math.acos(w) * 360 / 3.141592653589793));
if (derivType == 0) {
pdbATOM.append(JU.Escape.drawQuat(q, prefix, id, ptCenter, 1));
if (qtype == 'n' && isAmino) {
var ptH = (monomer).getNitrogenHydrogenPoint();
if (ptH != null) pdbATOM.append("draw ID \"").append(prefix).append("nh").append(id).append("\" width 0.1 ").append(JU.Escape.eP(ptH)).append("\n");
}}if (derivType == 1) {
pdbATOM.append(monomer.getHelixData(135176, qtype, mStep)).append("\n");
continue;
}pt.set(x * 2, y * 2, z * 2);
pdbATOM.append("draw ID \"").append(prefix).append("a").append(id).append("\" VECTOR ").append(JU.Escape.eP(ptCenter)).append(JU.Escape.eP(pt)).append(" \">").append(String.valueOf(deg)).append("\" color ").append(JM.BioExt.qColor[derivType]).append("\n");
continue;
}strExtra = JM.BioExt.getQInfo(q) + JU.PT.sprintf("  %10.5p %10.5p %10.5p", "p",  Clazz.newArray(-1, [ptCenter]));
if (qtype == 'n' && isAmino) {
strExtra += JU.PT.sprintf("  %10.5p %10.5p %10.5p", "p",  Clazz.newArray(-1, [(monomer).getNitrogenHydrogenPoint()]));
} else if (derivType == 2 && !Float.isNaN(val1)) {
strExtra += JU.PT.sprintf(" %10.5f %10.5f", "F",  Clazz.newArray(-1, [ Clazz.newFloatArray(-1, [val1, val2])]));
}}if (pdbATOM == null) continue;
bsWritten.set((a.group).leadAtomIndex);
pdbATOM.append(JM.LabelToken.formatLabelAtomArray(this.vwr, a, tokens, '\0', null, ptTemp));
pdbATOM.append(JU.PT.sprintf("%8.2f%8.2f%8.2f      %6.3f          %2s    %s\n", "ssF",  Clazz.newArray(-1, [a.getElementSymbolIso(false).toUpperCase(), strExtra,  Clazz.newFloatArray(-1, [x * factor, y * factor, z * factor, w * factor])])));
if (atomLast != null && atomLast.group.getBioPolymerIndexInModel() == a.group.getBioPolymerIndexInModel()) {
pdbCONECT.append("CONECT").append(JU.PT.formatStringI("%5i", "i", atomLast.getAtomNumber())).append(JU.PT.formatStringI("%5i", "i", a.getAtomNumber())).appendC('\n');
}atomLast = a;
}}
}, "~N,~N,JM.BioPolymer,~S,~S,~N,JU.BS,JU.BS,~B,~B,~B,~B,~B,~B,~N,~B,~B,~A,JU.OC,JU.SB,JU.BS,JU.P3");
c$.getQInfo = Clazz.defineMethod(c$, "getQInfo", 
function(q){
var axis = q.toAxisAngle4f();
return JU.PT.sprintf("%10.6f%10.6f%10.6f%10.6f  %6.2f  %10.5f %10.5f %10.5f", "F",  Clazz.newArray(-1, [ Clazz.newFloatArray(-1, [q.q0, q.q1, q.q2, q.q3, (axis.angle * 180 / 3.141592653589793), axis.x, axis.y, axis.z])]));
}, "JU.Quat");
c$.drawQuat = Clazz.defineMethod(c$, "drawQuat", 
function(q, prefix, id, ptCenter, scale){
var strV = " VECTOR " + JU.Escape.eP(ptCenter) + " ";
if (scale == 0) scale = 1;
return "draw " + prefix + "x" + id + strV + JU.Escape.eP(q.getVectorScaled(0, scale)) + " color red\n" + "draw " + prefix + "y" + id + strV + JU.Escape.eP(q.getVectorScaled(1, scale)) + " color green\n" + "draw " + prefix + "z" + id + strV + JU.Escape.eP(q.getVectorScaled(2, scale)) + " color blue\n";
}, "JU.Quat,~S,~S,JU.P3,~N");
c$.get3DStraightness = Clazz.defineMethod(c$, "get3DStraightness", 
function(id, dq, dqnext){
return dq.getNormal().dot(dqnext.getNormal());
}, "~S,JU.Quat,JU.Quat");
c$.getQuaternionStraightness = Clazz.defineMethod(c$, "getQuaternionStraightness", 
function(id, dq, dqnext){
return JM.BioExt.getStraightness(dq.dot(dqnext));
}, "~S,JU.Quat,JU.Quat");
c$.getStraightness = Clazz.defineMethod(c$, "getStraightness", 
function(cosHalfTheta){
return (1 - 2 * Math.acos(Math.abs(cosHalfTheta)) / 3.141592653589793);
}, "~N");
Clazz.defineMethod(c$, "getPdbDataM", 
function(m, vwr, type, ctype, isDraw, bsSelected, out, tokens, pdbCONECT, bsWritten){
var bothEnds = false;
var qtype = (ctype != 'R' ? 'r' : type.length > 13 && type.indexOf("ramachandran ") >= 0 ? type.charAt(13) : 'R');
if (qtype == 'r') qtype = vwr.getQuaternionFrame();
var mStep = vwr.getInt(553648142);
var derivType = (type.indexOf("diff") < 0 ? 0 : type.indexOf("2") < 0 ? 1 : 2);
if (!isDraw) {
out.append("REMARK   6 Jmol PDB-encoded data: " + type + ";");
if (ctype != 'R') {
out.append("  quaternionFrame = \"" + qtype + "\"");
bothEnds = true;
}out.append("\nREMARK   6 Jmol Version ").append(JV.Viewer.getJmolVersion()).append("\n");
if (ctype == 'R') out.append("REMARK   6 Jmol data min = {-180 -180 -180} max = {180 180 180} unScaledXyz = xyz * {1 1 1} + {0 0 0} plotScale = {100 100 100}\n");
 else out.append("REMARK   6 Jmol data min = {-1 -1 -1} max = {1 1 1} unScaledXyz = xyz * {0.1 0.1 0.1} + {0 0 0} plotScale = {100 100 100}\n");
}var ptTemp =  new JU.P3();
for (var p = 0; p < m.bioPolymerCount; p++) this.getPdbData(m.bioPolymers[p], ctype, qtype, mStep, derivType, m.bsAtoms, bsSelected, bothEnds, isDraw, p == 0, tokens, out, pdbCONECT, bsWritten, ptTemp);

}, "JM.BioModel,JV.Viewer,~S,~S,~B,JU.BS,JU.OC,~A,JU.SB,JU.BS");
Clazz.defineMethod(c$, "calculateAllstruts", 
function(vwr, ms, bs1, bs2){
vwr.setModelVisibility();
ms.makeConnections2(0, 3.4028235E38, 32768, 12291, bs1, bs2, null, false, false, 0, null);
var iAtom = bs1.nextSetBit(0);
if (iAtom < 0) return 0;
var m = ms.am[ms.at[iAtom].mi];
if (!m.isBioModel) return 0;
var vCA =  new JU.Lst();
var bsCheck;
if (bs1.equals(bs2)) {
bsCheck = bs1;
} else {
bsCheck = JU.BSUtil.copy(bs1);
bsCheck.or(bs2);
}var atoms = ms.at;
bsCheck.and(vwr.getModelUndeletedAtomsBitSet(m.modelIndex));
for (var i = bsCheck.nextSetBit(0); i >= 0; i = bsCheck.nextSetBit(i + 1)) {
var a = atoms[i];
if (a.checkVisible() && a.atomID == 2 && a.group.groupID != 5 && atoms[i].group.leadAtomIndex >= 0) vCA.addLast(atoms[i]);
}
if (vCA.size() == 0) return 0;
var struts = JM.BioExt.calculateStruts(ms, bs1, bs2, vCA, vwr.getFloat(570425408), vwr.getInt(553648183), vwr.getBoolean(603979955));
var mad = Clazz.floatToShort(vwr.getFloat(570425406) * 2000);
for (var i = 0; i < struts.size(); i++) {
var o = struts.get(i);
ms.bondAtoms(o[0], o[1], 32768, mad, null, 0, false, true);
}
return struts.size();
}, "JV.Viewer,JM.ModelSet,JU.BS,JU.BS");
c$.calculateStruts = Clazz.defineMethod(c$, "calculateStruts", 
function(modelSet, bs1, bs2, vCA, thresh, delta, allowMultiple){
var vStruts =  new JU.Lst();
var thresh2 = thresh * thresh;
var n = vCA.size();
var nEndMin = 3;
var bsStruts =  new JU.BS();
var bsNotAvailable =  new JU.BS();
var bsNearbyResidues =  new JU.BS();
var a1 = vCA.get(0);
var a2;
var nBiopolymers = modelSet.getBioPolymerCountInModel(a1.mi);
var biopolymerStartsEnds =  Clazz.newIntArray (nBiopolymers, nEndMin * 2, 0);
for (var i = 0; i < n; i++) {
a1 = vCA.get(i);
var polymerIndex = a1.group.getBioPolymerIndexInModel();
var monomerIndex = a1.group.getMonomerIndex();
var bpt = monomerIndex;
if (bpt < nEndMin) biopolymerStartsEnds[polymerIndex][bpt] = i + 1;
bpt = (a1.group).getBioPolymerLength() - monomerIndex - 1;
if (bpt < nEndMin) biopolymerStartsEnds[polymerIndex][nEndMin + bpt] = i + 1;
}
var d2 =  Clazz.newFloatArray (Clazz.doubleToInt(n * (n - 1) / 2), 0);
for (var i = 0; i < n; i++) {
a1 = vCA.get(i);
for (var j = i + 1; j < n; j++) {
var ipt = JM.BioExt.strutPoint(i, j, n);
a2 = vCA.get(j);
var resno1 = a1.getResno();
var polymerIndex1 = a1.group.getBioPolymerIndexInModel();
var resno2 = a2.getResno();
var polymerIndex2 = a2.group.getBioPolymerIndexInModel();
if (polymerIndex1 == polymerIndex2 && Math.abs(resno2 - resno1) < delta) bsNearbyResidues.set(ipt);
var d = d2[ipt] = a1.distanceSquared(a2);
if (d >= thresh2) bsNotAvailable.set(ipt);
}
}
for (var t = 5; --t >= 0; ) {
thresh2 = (thresh - t) * (thresh - t);
for (var i = 0; i < n; i++) if (allowMultiple || !bsStruts.get(i)) for (var j = i + 1; j < n; j++) {
var ipt = JM.BioExt.strutPoint(i, j, n);
if (!bsNotAvailable.get(ipt) && !bsNearbyResidues.get(ipt) && (allowMultiple || !bsStruts.get(j)) && d2[ipt] <= thresh2) JM.BioExt.setStrut(i, j, n, vCA, bs1, bs2, vStruts, bsStruts, bsNotAvailable, bsNearbyResidues, delta);
}

}
for (var b = 0; b < nBiopolymers; b++) {
for (var k = 0; k < nEndMin * 2; k++) {
var i = biopolymerStartsEnds[b][k] - 1;
if (i >= 0 && bsStruts.get(i)) {
for (var j = 0; j < nEndMin; j++) {
var pt = (Clazz.doubleToInt(k / nEndMin)) * nEndMin + j;
if ((i = biopolymerStartsEnds[b][pt] - 1) >= 0) bsStruts.set(i);
biopolymerStartsEnds[b][pt] = -1;
}
}}
if (biopolymerStartsEnds[b][0] == -1 && biopolymerStartsEnds[b][nEndMin] == -1) continue;
var okN = false;
var okC = false;
var iN = 0;
var jN = 0;
var iC = 0;
var jC = 0;
var minN = 3.4028235E38;
var minC = 3.4028235E38;
for (var j = 0; j < n; j++) for (var k = 0; k < nEndMin * 2; k++) {
var i = biopolymerStartsEnds[b][k] - 1;
if (i == -2) {
k = (Clazz.doubleToInt(k / nEndMin) + 1) * nEndMin - 1;
continue;
}if (j == i || i == -1) continue;
var ipt = JM.BioExt.strutPoint(i, j, n);
if (bsNearbyResidues.get(ipt) || d2[ipt] > (k < nEndMin ? minN : minC)) continue;
if (k < nEndMin) {
if (bsNotAvailable.get(ipt)) okN = true;
jN = j;
iN = i;
minN = d2[ipt];
} else {
if (bsNotAvailable.get(ipt)) okC = true;
jC = j;
iC = i;
minC = d2[ipt];
}}

if (okN) JM.BioExt.setStrut(iN, jN, n, vCA, bs1, bs2, vStruts, bsStruts, bsNotAvailable, bsNearbyResidues, delta);
if (okC) JM.BioExt.setStrut(iC, jC, n, vCA, bs1, bs2, vStruts, bsStruts, bsNotAvailable, bsNearbyResidues, delta);
}
return vStruts;
}, "JM.ModelSet,JU.BS,JU.BS,JU.Lst,~N,~N,~B");
c$.strutPoint = Clazz.defineMethod(c$, "strutPoint", 
function(i, j, n){
return (j < i ? Clazz.doubleToInt(j * (2 * n - j - 1) / 2) + i - j - 1 : Clazz.doubleToInt(i * (2 * n - i - 1) / 2) + j - i - 1);
}, "~N,~N,~N");
c$.setStrut = Clazz.defineMethod(c$, "setStrut", 
function(i, j, n, vCA, bs1, bs2, vStruts, bsStruts, bsNotAvailable, bsNearbyResidues, delta){
var a1 = vCA.get(i);
var a2 = vCA.get(j);
if (!bs1.get(a1.i) || !bs2.get(a2.i)) return;
vStruts.addLast( Clazz.newArray(-1, [a1, a2]));
bsStruts.set(i);
bsStruts.set(j);
for (var k1 = Math.max(0, i - delta); k1 <= i + delta && k1 < n; k1++) {
for (var k2 = Math.max(0, j - delta); k2 <= j + delta && k2 < n; k2++) {
if (k1 == k2) {
continue;
}var ipt = JM.BioExt.strutPoint(k1, k2, n);
if (!bsNearbyResidues.get(ipt)) {
bsNotAvailable.set(ipt);
}}
}
}, "~N,~N,~N,JU.Lst,JU.BS,JU.BS,JU.Lst,JU.BS,JU.BS,JU.BS,~N");
Clazz.defineMethod(c$, "mutate", 
function(vwr, bs, group, sequence, helixType, phipsi){
var addH = vwr.getBoolean(603979894);
if (sequence == null) return JM.BioExt.mutateAtom(vwr, bs.nextSetBit(0), group, addH);
var haveHelixType = (helixType != null);
var isCreate = (haveHelixType || phipsi != null);
if (isCreate) {
var isTurn = false;
if (haveHelixType) {
helixType = helixType.toLowerCase();
isTurn = (helixType.startsWith("turn"));
phipsi = this.getPhiPsiForHelixType(helixType);
if (phipsi == null) return false;
}var bs0 = vwr.getAllAtoms();
var nseq = sequence.length;
var nres = (haveHelixType && phipsi.length == 2 ? nseq : Math.max((haveHelixType ? 2 : 0) + Clazz.doubleToInt(phipsi.length / 2), nseq));
var gly =  Clazz.newIntArray (nres, 0);
for (var i = 0; i < nres; i++) {
gly[i] = (sequence[i % nseq].equals("GLY") ? 1 : 0);
}
JM.BioExt.createHelix(vwr, nres, gly, phipsi, isTurn);
bs = JU.BSUtil.andNot(vwr.getAllAtoms(), bs0);
}var isFile = (group == null);
if (isFile) group = sequence[0];
var groups = vwr.ms.getGroups();
var isOK = false;
for (var i = 0, pt = 0; i < groups.length; i++) {
var g = (groups[i].isProtein() ? groups[i] : null);
if (g == null || !g.isSelected(bs)) continue;
if (!isFile) {
group = sequence[pt++ % sequence.length];
if (group.equals("UNK") || isCreate && (group.equals("ALA") || group.equals("GLY"))) {
isOK = true;
continue;
}group = "==" + group;
}if (JM.BioExt.mutateAtom(vwr, g.firstAtomIndex, group, addH)) {
isOK = true;
}}
return isOK;
}, "JV.Viewer,JU.BS,~S,~A,~S,~A");
c$.createHelix = Clazz.defineMethod(c$, "createHelix", 
function(vwr, nRes, gly, phipsi, isTurn){
var script = JU.PT.rep(JU.PT.rep(JU.PT.rep(JU.PT.rep(JM.BioExt.helixScript, "$NRES", "" + nRes), "$PHIPSI", JU.PT.toJSON(null, phipsi)), "$GLY", JU.PT.toJSON(null, gly)), "$ISTURN", "" + isTurn);
try {
if (JU.Logger.debugging) JU.Logger.debug(script);
vwr.eval.runScript(script);
vwr.calculateStructures(vwr.getFrameAtoms(), true, true, -1);
} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
e.printStackTrace();
System.out.println(e);
} else {
throw e;
}
}
}, "JV.Viewer,~N,~A,~A,~B");
Clazz.defineMethod(c$, "getPhiPsiForHelixType", 
function(t){
t = t.toLowerCase().trim().$replace(' ', '-');
for (var i = JM.BioExt.alphaTypes.length - 2; i >= 0; i -= 2) {
if (t.equals(JM.BioExt.alphaTypes[i])) return JM.BioExt.alphaTypes[i + 1];
}
return null;
}, "~S");
c$.mutateAtom = Clazz.defineMethod(c$, "mutateAtom", 
function(vwr, iatom, fileName, addH){
var ms = vwr.ms;
var iModel = ms.at[iatom].mi;
var m = ms.am[iModel];
if (ms.isTrajectory(iModel)) return false;
var info = vwr.fm.getFileInfo();
var g = ms.at[iatom].group;
if (!(Clazz.instanceOf(g,"JM.AminoMonomer"))) return false;
(m).isMutated = true;
var res0 = g;
var ac = ms.ac;
var bsRes0 =  new JU.BS();
res0.setAtomBits(bsRes0);
bsRes0.and(vwr.getModelUndeletedAtomsBitSet(iModel));
var backbone = JM.BioExt.getMutationBackbone(res0, null);
fileName = JU.PT.esc(fileName);
var script = JU.PT.rep(JU.PT.rep(JM.BioExt.mutateScript, "$RES0", JU.BS.escape(bsRes0, '(', ')')), "$FNAME", fileName);
try {
if (JU.Logger.debugging) JU.Logger.debug(script);
vwr.eval.runScript(script);
} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
e.printStackTrace();
System.out.println(e);
} else {
throw e;
}
}
ms = vwr.ms;
if (ms.ac == ac) return false;
m = ms.am[iModel];
var sb = m.loadScript;
var s = JU.PT.rep(sb.toString(), "load mutate ", "mutate ({" + iatom + "})");
sb.setLength(0);
sb.append(s);
var bs = vwr.getModelUndeletedAtomsBitSet(iModel);
var ia = bs.length() - 1;
if (ms.at[ia] == null) {
System.out.println("BioExt fail ");
return false;
}g = ms.at[ia].group;
if (g !== ms.at[ac + 1].group || !(Clazz.instanceOf(g,"JM.AminoMonomer"))) {
var bsAtoms =  new JU.BS();
g.setAtomBits(bsAtoms);
vwr.deleteAtoms(bsAtoms, false);
return false;
}var res1 = g;
JM.BioExt.getMutationBackbone(res1, backbone);
JM.BioExt.replaceMutatedMonomer(vwr, res0, res1, addH);
vwr.fm.setFileInfo(info);
return true;
}, "JV.Viewer,~N,~S,~B");
c$.replaceMutatedMonomer = Clazz.defineMethod(c$, "replaceMutatedMonomer", 
function(vwr, res0, res1, addH){
res1.setResno(res0.getResno());
res1.monomerIndex = res0.monomerIndex;
res1.seqcode = res0.seqcode;
res1.chain.groupCount = 0;
res1.chain = res0.chain;
res1.chain.model.groupCount = -1;
res1.proteinStructure = res0.proteinStructure;
vwr.shm.replaceGroup(res0, res1);
var groups = res0.chain.groups;
for (var i = groups.length; --i >= 0; ) if (groups[i] === res0) {
groups[i] = res1;
break;
}
res1.bioPolymer = res0.bioPolymer;
if (res1.bioPolymer != null) {
var m = res1.bioPolymer.monomers;
for (var j = m.length; --j >= 0; ) if (m[j] === res0) {
m[j] = res1;
break;
}
}res1.bioPolymer.recalculateLeadMidpointsAndWingVectors();
if (addH) {
JM.BioExt.fixHydrogens(vwr, res1);
}}, "JV.Viewer,JM.AminoMonomer,JM.AminoMonomer,~B");
c$.fixHydrogens = Clazz.defineMethod(c$, "fixHydrogens", 
function(vwr, res1){
var a = res1.getNitrogenAtom();
switch (a.getBondCount() * 10 + a.getCovalentHydrogenCount()) {
case 32:
a.setFormalCharge(1);
var p = vwr.getAdditionalHydrogens(JU.BSUtil.newAndSetBit(a.i), null, 4096);
if (p.length == 1) {
var vConnections =  new JU.Lst();
vConnections.addLast(a);
var b = vwr.ms.addAtom(a.mi, a.group, 1, "H3", null, 0, a.getSeqID(), 0, p[0], NaN, null, 0, 0, 1, 0, null, a.isHetero(), 0, null, NaN);
vwr.ms.bondAtoms(a, b, 1, vwr.ms.getDefaultMadFromOrder(1), null, 0, true, false);
b.setMadAtom(vwr, vwr.rd);
}break;
case 3:
break;
}
}, "JV.Viewer,JM.AminoMonomer");
c$.getMutationBackbone = Clazz.defineMethod(c$, "getMutationBackbone", 
function(res, backbone){
var b =  Clazz.newArray(-1, [res.getCarbonylCarbonAtom(), res.getCarbonylOxygenAtom(), res.getLeadAtom(), res.getNitrogenAtom(), res.getExplicitNH()]);
if (backbone == null) {
if (b[3].getCovalentHydrogenCount() > 1) b[4] = null;
} else {
for (var i = 0; i < 5; i++) {
var a0 = backbone[i];
var a1 = b[i];
if (a0 != null && a1 != null) a1.setT(a0);
}
}return b;
}, "JM.AminoMonomer,~A");
Clazz.defineMethod(c$, "getFullPDBHeader", 
function(auxiliaryInfo){
var info = this.vwr.getCurrentFileAsString("biomodel");
var ichMin = info.length;
for (var i = JM.BioExt.pdbRecords.length; --i >= 0; ) {
var ichFound;
var strRecord = JM.BioExt.pdbRecords[i];
switch (ichFound = (info.startsWith(strRecord) ? 0 : info.indexOf("\n" + strRecord))) {
case -1:
continue;
case 0:
auxiliaryInfo.put("fileHeader", "");
return "";
default:
if (ichFound < ichMin) ichMin = ++ichFound;
}
}
info = info.substring(0, ichMin);
auxiliaryInfo.put("fileHeader", info);
return info;
}, "java.util.Map");
Clazz.defineMethod(c$, "getAminoAcidValenceAndCharge", 
function(res, name, ret){
var valence = ret[4];
ret[4] = 0;
if (res == null || res.length == 0 || res.length > 3 || name.equals("CA") || name.equals("CB")) return false;
var ch0 = name.charAt(0);
var ch1 = (name.length == 1 ? '\0' : name.charAt(1));
var isSp2 = false;
var bondCount = ret[3];
switch (res.length) {
case 3:
if (name.length == 1) {
switch ((ch0).charCodeAt(0)) {
case 78:
if (bondCount > 1) return false;
ret[1] = 1;
break;
case 79:
if (valence == 1) {
return true;
}isSp2 = ("HOH;DOD;WAT".indexOf(res) < 0);
break;
default:
isSp2 = true;
}
} else {
var id = res + ch0;
isSp2 = ("ARGN;ASNN;ASNO;ASPO;GLNN;GLNO;GLUO;HISN;HISC;PHECTRPC;TRPN;TYRC".indexOf(id) >= 0);
if ("LYSN".indexOf(id) >= 0) {
ret[1] = 1;
} else if (ch0 == 'O' && ch1 == 'X') {
ret[1] = -1;
}}break;
case 1:
case 2:
if (name.length > 2 && name.charAt(2) == '\'') return false;
switch ((ch0).charCodeAt(0)) {
case 67:
if (ch1 == '7') return false;
break;
case 78:
switch ((ch1).charCodeAt(0)) {
case 49:
case 51:
if ("A3;A1;C3;G3;I3".indexOf("" + res.charAt(res.length - 1) + ch1) >= 0) ret[0]--;
break;
case 55:
ret[0]--;
break;
}
break;
}
isSp2 = true;
}
if (isSp2) {
ret[4] = ("ARGNE;ARGNH1;ASNNH2;GLNNE2;TRPNE1;HISNE2".indexOf(res + name) >= 0 ? 0 : 1);
switch ((ch0).charCodeAt(0)) {
case 78:
ret[2] = 2;
if (valence == 2 && bondCount == 1) ret[4]++;
break;
case 67:
ret[2] = 2;
ret[0]--;
break;
case 79:
if (valence == 2 && bondCount == 1) ret[4]--;
ret[0]--;
break;
}
}return true;
}, "~S,~S,~A");
c$.qColor =  Clazz.newArray(-1, ["yellow", "orange", "purple"]);
c$.helixScript = "var nRes = $NRES; var a = $PHIPSI; var isTurn = $ISTURN;var gly=$GLY\nvar phi = a[1];\nvar psi = a[2];\nif (nRes == 0) nRes = 10;\nvar isRandomPhi = (phi == 999)\nvar isRandomPsi = (psi == 999)\nvar a0 = {*};\nvar pdbadd = pdbAddHydrogens;pdbAddHydrogens = false\ndata \"append mydata\"\nATOM      1  N   ALA     0      -0.499   1.323   0.000  1.00 13.99           N  \nATOM      2  CA  ALA     0       0.000   0.000   0.000  1.00 20.10           C  \nATOM      3  C   ALA     0       1.461   0.000   0.000  1.00 17.07           C  \nATOM      4  O   ALA     0       2.110  -1.123   0.000  1.00 17.78           O  \nATOM      5  CB  ALA     0      -0.582  -0.697  -1.291  1.00 13.05           C  \nATOM      6  OXT ALA     0       2.046   1.197   0.000  1.00 13.05           O  \nend \"append mydata\"\nset appendnew false\ndata \"mydata\"\nATOM   0001  N   ALA     0      -0.499   1.323   0.000  1.00 13.99           N  \nATOM   0002  CA  ALA     0       0.000   0.000   0.000  1.00 20.10           C  \nATOM   0003  C   ALA     0       1.461   0.000   0.000  1.00 17.07           C  \nATOM   0004  O   ALA     0       2.110  -1.123   0.000  1.00 17.78           O  \nATOM   0005  OXT ALA     0       2.046   1.197   0.000  1.00 13.05           O  \nATOM   0006  CB  ALA     0      -0.582  -0.697  -1.291  1.00 13.05           C  \nend \"mydata\"\nvar C2 = null;\nvar apt = -2\nvar nangle = a.length\nfor (var i = 1; i <= nRes; i++) {\n  if (isTurn && (i == 2 || i == nRes))apt -= 2\n  apt = (apt + 2)%nangle\n  phi = a[apt + 1]\n  psi = a[apt + 2]\n  if (isRandomPhi){\n     phi = random(360) - 180\n  }\n  if (isRandomPsi){\n     psi = random(360) - 180\n  }\n  select !a0;\n  rotateselected molecular {0 0 0} {0 0 1} -69\n  var C = (C2 ? C2 : {!a0 & *.C}[0]);\n  translateselected @{-C.xyz}\n  rotateselected molecular {0 0 0} {0 0 1} 9\n  translateselected {-1.461 0 0}\n  rotateselected molecular {0 0 0} {0 0 1} -9\n  var a1 = {*};\n  var sdata = data(\"mydata\")\n  sdata = sdata.replace(\'  0   \',(\'  \'+i)[-2][0] + \'   \')\n  if (gly[((i-1)%nRes) + 1]) { sdata = sdata.replace(\'ALA\',\'GLY\').split(\'ATOM   0006\')[1]}\n  var n = a1.size\n  sdata = sdata.replace(\'0001\',(\'   \'+(n+1))[-3][0])\n  sdata = sdata.replace(\'0002\',(\'   \'+(n+2))[-3][0])\n  sdata = sdata.replace(\'0003\',(\'   \'+(n+3))[-3][0])\n  sdata = sdata.replace(\'0004\',(\'   \'+(n+4))[-3][0])\n  sdata = sdata.replace(\'0005\',(\'   \'+(n+5))[-3][0])\n  sdata = sdata.replace(\'0006\',(\'   \'+(n+6))[-3][0])\n  data \"append @sdata\"\n  var N = {!a1 && *.N}[0]\n  connect @N @C\n  select !a1\n  translateselected @{-N.xyz}\n  C2  = {!a1 && *.C}[0]\n  var CA = {!a1 && *.CA}[0]\n  select @{within(\'branch\',C2,CA)}\n  rotateSelected @C2 @CA @psi\n  select @{within(\'branch\',CA,N)}\n  rotateSelected @CA @N @{180 + phi}\n}\n  var xt = {*.OXT}[1][-1];\n  delete 0 or *.HXT or xt;\n  pdbAddHydrogens = pdbadd;\n  select !a0;var a=-{selected}.xyz;\n  translateSelected @a\n  var pdbdata = data(!a0, \'PDB\');\n  if (a0) {\n    delete !a0;\n    data \"append model @pdbdata\";\n    set appendnew true\n  } else {\n    data \"model @pdbdata\";\n  }\n var vr = {resno=2}[0]\n  var v = helix(within(group,vr),\'axis\')\n  var vrot = cross(v, {0 0 1})\n  rotateselected molecular {0 0 0} @vrot @{angle(v, {0 0 0}, {0 0 1})}\n  set appendnew true\n  pdbSequential = ispdbseq;\n";
c$.alphaTypes =  Clazz.newArray(-1, ["alpha",  Clazz.newFloatArray(-1, [-65, -40]), "3-10",  Clazz.newFloatArray(-1, [-74, -4]), "pi",  Clazz.newFloatArray(-1, [-57.1, -69.7]), "alpha-l",  Clazz.newFloatArray(-1, [57.1, 4]), "helix-ii",  Clazz.newFloatArray(-1, [-79, 150]), "collagen",  Clazz.newFloatArray(-1, [-51, 153]), "beta",  Clazz.newFloatArray(-1, [-140, 130]), "beta-120",  Clazz.newFloatArray(-1, [-120, 120]), "beta-135",  Clazz.newFloatArray(-1, [-135, 135]), "extended",  Clazz.newFloatArray(-1, [180, 180]), "turn-i",  Clazz.newFloatArray(-1, [-60, -30, -90, 0]), "turn-ii",  Clazz.newFloatArray(-1, [-60, 120, 80, 0]), "turn-iii",  Clazz.newFloatArray(-1, [-60, -30, -60, -30]), "turn-i'",  Clazz.newFloatArray(-1, [60, 30, 90, 0]), "turn-ii'",  Clazz.newFloatArray(-1, [60, -120, -80, 0]), "turn-iii'",  Clazz.newFloatArray(-1, [60, 30, 60, 30])]);
c$.mutateScript = "try{\n  var a0 = {*}\n  var res0 = $RES0\n  load mutate $FNAME\n  var res1 = {!a0};var r1 = res1[1];var r0 = res1[0]\n  if ({r1 & within(group, r0)}){\n    var haveHs = ({_H & connected(res0)} != 0)\n    var rh = {_H} & res1;\n    if (!haveHs) {delete rh; res1 = res1 & !rh}\n    var sm = \'[*.N][*.CA][*.C][*.O]\'\n    var keyatoms = res1.find(sm)\n    var x = compare(res1,res0,sm,\'BONDS\')\n    if(x){\n      var allN = {*.N};var allCA = {*.cA};var allC = {*.C}; var allO = {*.O}; var allH = {*.H}\n      print \'mutating \' + res0[1].label(\'%n%r\') + \' to \' + $FNAME.trim(\'=\')\n      rotate branch @x\n;      compare @res1 @res0 SMARTS \'[*.N][*.CA][*.C]\' rotate translate 0\n      var c = {!res0 & connected(res0)}\n      var N2 = {allN & c}\n      var C0 = {allC & c}\n      {allN & res1}.xyz = {allN & res0}.xyz\n      {allCA & res1}.xyz = {allCA & res0}.xyz\n      {allC & res1}.xyz = {allC & res0}.xyz\n      if (N2) {allO & res1}.xyz = {allO & res0}.xyz\n      var NH = {_H & res0 && connected(allN)}\n      var angleH = ({*.H and res0} ? angle({allC and res0},{allCA and res0},{allN and res0},NH) : 1000)\n      delete res0\n      if (N2) {\n        delete (*.OXT,*.HXT) and res1\n        connect {N2} {keyatoms & *.C}\n      } else {\n        delete (*.HXT) and res1\n        {*.OXT & res1}.formalCharge = -1\n      }\n      var N1 = {allN & res1}\n      var H1 = {allH and res1}\n      var NH = {H1 & connected(N1)}\n      if (C0) {\n        switch (0 + NH) {\n        case 0:\n          break\n        case 1:\n          delete H1\n          break\n        default:\n          var CA1 = {allCA & res1}\n          x = angle({allC and res1},CA1,N1,NH)\n          rotate branch @CA1 @N1 @{angleH-x}\n          delete *.H2 and res1\n          delete *.H3 and res1\n          break\n        }\n        connect {C0} {keyatoms & allN}\n      }\n    }\n  }\n}catch(e){print e}\n";
c$.pdbRecords =  Clazz.newArray(-1, ["ATOM  ", "MODEL ", "HETATM"]);
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024

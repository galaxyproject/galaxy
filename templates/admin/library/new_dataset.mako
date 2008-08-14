<%inherit file="/base.mako"/>

<%def name="title()">Create New Library Dataset</%def>
<div class="toolForm" id="new_dataset">
  <div class="form-row">
    <a href="${h.url_for( controller='admin', action='libraries' )}">Libraries</a>&nbsp;&nbsp;|&nbsp;&nbsp;
    <a href="${h.url_for( controller='admin', action='groups' )}">Groups</a>&nbsp;&nbsp;|&nbsp;&nbsp;
    <tr><td><a href="${h.url_for( controller='admin', action='users' )}">Users</a></td></tr>
  </div>
  <div class="toolFormTitle">Create a new Library Dataset</div>
  <div class="toolFormBody">
    <form name="tool_form" action="${h.url_for( controller='admin', action='dataset' )}" enctype="multipart/form-data" method="post">
      <input type="hidden" name="folder_id" value="${folder_id}">
      <div class="form-row">
        <label>File:</label>
        <div style="float: left; width: 250px; margin-right: 10px;"><input type="file" name="file_data"></div>
        <div style="clear: both"></div>
      </div>
      <div class="form-row">
        <label>URL/Text:</label>
        <div style="float: left; width: 250px; margin-right: 10px;"><textarea name="url_paste" rows="5" cols="35"></textarea></div>
        <div class="toolParamHelp" style="clear: both;">
          Here you may specify a list of URLs (one per line) or paste the contents of a file.
        </div>
        <div style="clear: both"></div>
      </div>
      <div class="form-row">
        <label>Convert spaces to tabs:</label>
        <div style="float: left; width: 250px; margin-right: 10px;"><div><input type="checkbox" name="space_to_tab" value="Yes">Yes</div></div>
        <div class="toolParamHelp" style="clear: both;">
          Use this option if you are entering intervals by hand.
        </div>
        <div style="clear: both"></div>
      </div>
      <div class="form-row">
        <label>File Format:</label>
        <div style="float: left; width: 250px; margin-right: 10px;">
          <select name="extension">
            <option value="auto" selected>Auto-detect</option>
            <option value="ab1">ab1</option>
            <option value="axt">axt</option>
            <option value="bed">bed</option>
            <option value="binseq.zip">binseq.zip</option>
            <option value="fasta">fasta</option>
            <option value="fastqsolexa">fastqsolexa</option>
            <option value="gff">gff</option>
            <option value="gff3">gff3</option>
            <option value="interval">interval</option>
            <option value="lav">lav</option>
            <option value="maf">maf</option>
            <option value="qual">qual</option>
            <option value="scf">scf</option>
            <option value="tabular">tabular</option>
            <option value="taxonomy">taxonomy</option>
            <option value="txt">txt</option>
            <option value="txtseq.zip">txtseq.zip</option>
            <option value="wig">wig</option>
          </select>
        </div>
        <div class="toolParamHelp" style="clear: both;">
          Which format? See help below
        </div>
        <div style="clear: both"></div>
      </div>
      <div class="form-row">
        <label>Genome:</label>
        ##this should be generated dynamically
        <div style="float: left; width: 250px; margin-right: 10px;">
        <select name="dbkey">
            <option value="?" selected>unspecified (?)</option>
            <option value="anoGam1">A. gambiae Feb. 2003 (anoGam1)</option>
            <option value="apiMel2">A. mellifera Jan. 2005 (apiMel2)</option>
            <option value="apiMel1">A. mellifera July 2004 (apiMel1)</option>
            <option value="acidCryp_JF_5">Acidiphilium cryptum JF-5 (acidCryp_JF_5)</option>
            <option value="acidBact_ELLIN345">Acidobacteria bacterium Ellin345 (acidBact_ELLIN345)</option>
            
            <option value="acidCell_11B">Acidothermus cellulolyticus 11B (acidCell_11B)</option>
            <option value="acidJS42">Acidovorax sp. JS42 (acidJS42)</option>
            <option value="acinSp_ADP1">Acinetobacter sp. ADP1 (acinSp_ADP1)</option>
            <option value="actiPleu_L20">Actinobacillus pleuropneumoniae L20 (actiPleu_L20)</option>
            <option value="aeroHydr_ATCC7966">Aeromonas hydrophila subsp. hydrophila ATCC 7966 (aeroHydr_ATCC7966)</option>
            <option value="aerPer1">Aeropyrum pernix K1 (aerPer1)</option>
            <option value="afrOth13">Afrotheria Apr. 24. 2006 (afrOth13)</option>
            <option value="alcaBork_SK2">Alcanivorax borkumensis SK2 (alcaBork_SK2)</option>
            <option value="alkaEhrl_MLHE_1">Alkalilimnicola ehrlichei MLHE-1 (alkaEhrl_MLHE_1)</option>
            
            <option value="anabVari_ATCC29413">Anabaena variabilis ATCC 29413 (anabVari_ATCC29413)</option>
            <option value="anaeDeha_2CP_C">Anaeromyxobacter dehalogenans 2CP-C (anaeDeha_2CP_C)</option>
            <option value="anapMarg_ST_MARIES">Anaplasma marginale str. St. Maries (anapMarg_ST_MARIES)</option>
            <option value="aquiAeol">Aquifex aeolicus VF5 (aquiAeol)</option>
            <option value="archFulg1">Archaeoglobus fulgidus DSM 4304 (archFulg1)</option>
            <option value="dasNov1">Armadillo May 2005 (dasNov1)</option>
            <option value="arthFB24">Arthrobacter sp. FB24 (arthFB24)</option>
            <option value="azoaSp_EBN1">Azoarcus sp. EbN1 (azoaSp_EBN1)</option>
            <option value="azorCaul2">Azorhizobium caulinodans ORS 571 (azorCaul2)</option>
            
            <option value="baciAnth_AMES">Bacillus anthracis str. Ames (baciAnth_AMES)</option>
            <option value="baciHalo">Bacillus halodurans C-125 (baciHalo)</option>
            <option value="baciSubt">Bacillus subtilis subsp. subtilis str. 168 (baciSubt)</option>
            <option value="bactThet_VPI_5482">Bacteroides thetaiotaomicron VPI-5482 (bactThet_VPI_5482)</option>
            <option value="bartHens_HOUSTON_1">Bartonella henselae str. Houston-1 (bartHens_HOUSTON_1)</option>
            <option value="baumCica_HOMALODISCA">Baumannia cicadellinicola str. Hc (Homalodisca coagulata) (baumCica_HOMALODISCA)</option>
            <option value="bdelBact">Bdellovibrio bacteriovorus HD100 (bdelBact)</option>
            <option value="bifiLong">Bifidobacterium longum NCC2705 (bifiLong)</option>
            <option value="bordBron">Bordetella bronchiseptica RB50 (bordBron)</option>
            
            <option value="borEut13">Boreoeutherian Apr. 24. 2006 (borEut13)</option>
            <option value="canHg12">Boreoeutherian Nov. 19. 2005 (canHg12)</option>
            <option value="borrBurg">Borrelia burgdorferi B31 (borrBurg)</option>
            <option value="bradJapo">Bradyrhizobium japonicum USDA 110 (bradJapo)</option>
            <option value="brucMeli">Brucella melitensis 16M (brucMeli)</option>
            <option value="buchSp">Buchnera aphidicola str. APS (Acyrthosiphon pisum) (buchSp)</option>
            <option value="burkCepa_AMMD">Burkholderia ambifaria AMMD (burkCepa_AMMD)</option>
            <option value="burkCeno_AU_1054">Burkholderia cenocepacia AU 1054 (burkCeno_AU_1054)</option>
            <option value="burkCeno_HI2424">Burkholderia cenocepacia HI2424 (burkCeno_HI2424)</option>
            
            <option value="burkMall_ATCC23344">Burkholderia mallei ATCC 23344 (burkMall_ATCC23344)</option>
            <option value="burkPseu_1106A">Burkholderia pseudomallei 1106a (burkPseu_1106A)</option>
            <option value="burk383">Burkholderia sp. 383 (burk383)</option>
            <option value="burkThai_E264">Burkholderia thailandensis E264 (burkThai_E264)</option>
            <option value="burkViet_G4">Burkholderia vietnamiensis G4 (burkViet_G4)</option>
            <option value="burkXeno_LB400">Burkholderia xenovorans LB400 (burkXeno_LB400)</option>
            <option value="otoGar1">Bushbaby Dec. 2006 (otoGar1)</option>
            <option value="caePb1">C. brenneri Jan. 2007 (caePb1)</option>
            <option value="cb3">C. briggsae Jan. 2007 (cb3)</option>
            
            <option value="cb2">C. briggsae Aug 2005 (cb2)</option>
            <option value="cb1">C. briggsae July 2002 (cb1)</option>
            <option value="ce4">C. elegans Jan. 2007 (ce4)</option>
            <option value="ce3">C. elegans March 2005 (ce3)</option>
            <option value="ce2">C. elegans Mar. 2004 (ce2)</option>
            <option value="ce1">C. elegans May 2003 (ce1)</option>
            <option value="ci2">C. intestinalis Mar. 2005 (ci2)</option>
            <option value="ci1">C. intestinalis Dec. 2002 (ci1)</option>
            <option value="caeRem2">C. remanei Mar. 2006 (caeRem2)</option>
            
            <option value="caeRem1">C. remanei March 2005 (caeRem1)</option>
            <option value="cioSav2">C. savignyi July 2005 (cioSav2)</option>
            <option value="cioSav1">C. savignyi Sept. 2001 (cioSav1)</option>
            <option value="caldSacc_DSM8903">Caldicellulosiruptor saccharolyticus DSM 8903 (caldSacc_DSM8903)</option>
            <option value="caldMaqu1">Caldivirga maquilingensis IC-167 (caldMaqu1)</option>
            <option value="campFetu_82_40">Campylobacter fetus subsp. fetus 82-40 (campFetu_82_40)</option>
            <option value="campJeju1">Campylobacter jejuni 02/25/2000 (campJeju1)</option>
            <option value="campJeju">Campylobacter jejuni subsp. jejuni NCTC 11168 (campJeju)</option>
            <option value="campJeju_RM1221">Campylobacter jejuni RM1221 (campJeju_RM1221)</option>
            
            <option value="campJeju_RM1221_1">Campylobacter jejuni RM1221 01/07/2005 (campJeju_RM1221_1)</option>
            <option value="campJeju_81_176">Campylobacter jejuni subsp. jejuni 81-176 (campJeju_81_176)</option>
            <option value="blocFlor">Candidatus Blochmannia floridanus (blocFlor)</option>
            <option value="candCars_RUDDII">Candidatus Carsonella ruddii PV (candCars_RUDDII)</option>
            <option value="methBoon1">Candidatus Methanoregula boonei 6A8 (methBoon1)</option>
            <option value="candPela_UBIQUE_HTCC1">Candidatus Pelagibacter ubique HTCC1062 (candPela_UBIQUE_HTCC1)</option>
            <option value="paraSp_UWE25">Candidatus Protochlamydia amoebophila UWE25 (paraSp_UWE25)</option>
            <option value="carbHydr_Z_2901">Carboxydothermus hydrogenoformans Z-2901 (carbHydr_Z_2901)</option>
            <option value="felCat3">Cat Mar. 2006 (felCat3)</option>
            
            <option value="catArr1">Catarrhini June 13. 2006 (catArr1)</option>
            <option value="caulCres">Caulobacter crescentus CB15 (caulCres)</option>
            <option value="galGal3">Chicken May 2006 (galGal3)</option>
            <option value="galGal2">Chicken Feb. 2004 (galGal2)</option>
            <option value="panTro2">Chimp Mar. 2006 (panTro2)</option>
            <option value="panTro1">Chimp Nov. 2003 (panTro1)</option>
            <option value="chlaTrac">Chlamydia trachomatis D/UW-3/CX (chlaTrac)</option>
            <option value="chlaPneu_CWL029">Chlamydophila pneumoniae CWL029 (chlaPneu_CWL029)</option>
            <option value="chloChlo_CAD3">Chlorobium chlorochromatii CaD3 (chloChlo_CAD3)</option>
            
            <option value="chloTepi_TLS">Chlorobium tepidum TLS (chloTepi_TLS)</option>
            <option value="chroViol">Chromobacterium violaceum ATCC 12472 (chroViol)</option>
            <option value="chroSale_DSM3043">Chromohalobacter salexigens DSM 3043 (chroSale_DSM3043)</option>
            <option value="clavMich_NCPPB_382">Clavibacter michiganensis subsp. michiganensis NCPPB 382 (clavMich_NCPPB_382)</option>
            <option value="colwPsyc_34H">Colwellia psychrerythraea 34H (colwPsyc_34H)</option>
            <option value="coryEffi_YS_314">Corynebacterium efficiens YS-314 (coryEffi_YS_314)</option>
            <option value="bosTau4">Cow Oct. 2007 (bosTau4)</option>
            <option value="bosTau3">Cow Aug. 2006 (bosTau3)</option>
            <option value="bosTau2">Cow Mar. 2005 (bosTau2)</option>
            
            <option value="bosTau1">Cow Sep. 2004 (bosTau1)</option>
            <option value="coxiBurn">Coxiella burnetii RSA 493 (coxiBurn)</option>
            <option value="cytoHutc_ATCC33406">Cytophaga hutchinsonii ATCC 33406 (cytoHutc_ATCC33406)</option>
            <option value="droAna2">D. ananassae Aug. 2005 (droAna2)</option>
            <option value="droAna1">D. ananassae July 2004 (droAna1)</option>
            <option value="droEre1">D. erecta Aug. 2005 (droEre1)</option>
            <option value="droGri1">D. grimshawi Aug. 2005 (droGri1)</option>
            <option value="dm3">D. melanogaster Apr. 2006 (dm3)</option>
            <option value="dm2">D. melanogaster Apr. 2004 (dm2)</option>
            
            <option value="dm1">D. melanogaster Jan. 2003 (dm1)</option>
            <option value="droMoj2">D. mojavensis Aug. 2005 (droMoj2)</option>
            <option value="droMoj1">D. mojavensis Aug. 2004 (droMoj1)</option>
            <option value="droPer1">D. persimilis Oct. 2005 (droPer1)</option>
            <option value="dp3">D. pseudoobscura Nov. 2004 (dp3)</option>
            <option value="dp2">D. pseudoobscura Aug. 2003 (dp2)</option>
            <option value="droSec1">D. sechellia Oct. 2005 (droSec1)</option>
            <option value="droSim1">D. simulans Apr. 2005 (droSim1)</option>
            <option value="droVir2">D. virilis Aug. 2005 (droVir2)</option>
            
            <option value="droVir1">D. virilis July 2004 (droVir1)</option>
            <option value="droYak2">D. yakuba Nov. 2005 (droYak2)</option>
            <option value="droYak1">D. yakuba Apr. 2004 (droYak1)</option>
            <option value="dechArom_RCB">Dechloromonas aromatica RCB (dechArom_RCB)</option>
            <option value="dehaEthe_195">Dehalococcoides ethenogenes 195 (dehaEthe_195)</option>
            <option value="deinGeot_DSM11300">Deinococcus geothermalis DSM 11300 (deinGeot_DSM11300)</option>
            <option value="deinRadi">Deinococcus radiodurans R1 (deinRadi)</option>
            <option value="desuHafn_Y51">Desulfitobacterium hafniense Y51 (desuHafn_Y51)</option>
            <option value="desuPsyc_LSV54">Desulfotalea psychrophila LSv54 (desuPsyc_LSV54)</option>
            
            <option value="desuRedu_MI_1">Desulfotomaculum reducens MI-1 (desuRedu_MI_1)</option>
            <option value="desuVulg_HILDENBOROUG">Desulfovibrio vulgaris subsp. vulgaris str. Hildenborough (desuVulg_HILDENBOROUG)</option>
            <option value="dichNodo_VCS1703A">Dichelobacter nodosus VCS1703A (dichNodo_VCS1703A)</option>
            <option value="canFam2">Dog May 2005 (canFam2)</option>
            <option value="canFam1">Dog July 2004 (canFam1)</option>
            <option value="ehrlRumi_WELGEVONDEN">Ehrlichia ruminantium str. Welgevonden (ehrlRumi_WELGEVONDEN)</option>
            <option value="loxAfr1">Elephant May 2005 (loxAfr1)</option>
            <option value="ente638">Enterobacter sp. 638 (ente638)</option>
            <option value="enteFaec_V583">Enterococcus faecalis V583 (enteFaec_V583)</option>
            
            <option value="erytLito_HTCC2594">Erythrobacter litoralis HTCC2594 (erytLito_HTCC2594)</option>
            <option value="eschColi_APEC_O1">Escherichia coli APEC O1 (eschColi_APEC_O1)</option>
            <option value="eschColi_CFT073">Escherichia coli CFT073 (eschColi_CFT073)</option>
            <option value="eschColi_CFT073_1">Escherichia coli CFT073 12/10/2002 (eschColi_CFT073_1)</option>
            <option value="eschColi_K12">Escherichia coli K12 (eschColi_K12)</option>
            <option value="eschColi_K12_1">Escherichia coli K12 09/05/1997 (eschColi_K12_1)</option>
            <option value="eschColi_O157H7">Escherichia coli O157:H7 str. Sakai (eschColi_O157H7)</option>
            <option value="eschColi_O157H7_1">Escherichia coli O157H7 03/29/2000 (eschColi_O157H7_1)</option>
            <option value="eschColi_O157H7EDL933_1">Escherichia coli O157H7 EDL933 02/24/2001 (eschColi_O157H7EDL933_1)</option>
            
            <option value="euaGli13">Euarchontoglires Apr. 24. 2006 (euaGli13)</option>
            <option value="eutHer13">Eutheria Apr. 24. 2006 (eutHer13)</option>
            <option value="flavJohn_UW101">Flavobacterium johnsoniae UW101 (flavJohn_UW101)</option>
            <option value="franTula_TULARENSIS">Francisella tularensis subsp. tularensis SCHU S4 (franTula_TULARENSIS)</option>
            <option value="franCcI3">Frankia sp. CcI3 (franCcI3)</option>
            <option value="fr2">Fugu Oct. 2004 (fr2)</option>
            <option value="fr1">Fugu Aug. 2002 (fr1)</option>
            <option value="fusoNucl">Fusobacterium nucleatum subsp. nucleatum ATCC 25586 (fusoNucl)</option>
            <option value="geobKaus_HTA426">Geobacillus kaustophilus HTA426 (geobKaus_HTA426)</option>
            
            <option value="geobTher_NG80_2">Geobacillus thermodenitrificans NG80-2 (geobTher_NG80_2)</option>
            <option value="geobMeta_GS15">Geobacter metallireducens GS-15 (geobMeta_GS15)</option>
            <option value="geobSulf">Geobacter sulfurreducens PCA (geobSulf)</option>
            <option value="geobUran_RF4">Geobacter uraniireducens Rf4 (geobUran_RF4)</option>
            <option value="gliRes13">Glires Apr. 24. 2006 (gliRes13)</option>
            <option value="gloeViol">Gloeobacter violaceus PCC 7421 (gloeViol)</option>
            <option value="glucOxyd_621H">Gluconobacter oxydans 621H (glucOxyd_621H)</option>
            <option value="gramFors_KT0803">Gramella forsetii KT0803 (gramFors_KT0803)</option>
            <option value="granBeth_CGDNIH1">Granulibacter bethesdensis CGDNIH1 (granBeth_CGDNIH1)</option>
            
            <option value="haemInfl_KW20">Haemophilus influenzae Rd KW20 (haemInfl_KW20)</option>
            <option value="haemSomn_129PT">Haemophilus somnus 129PT (haemSomn_129PT)</option>
            <option value="haheChej_KCTC_2396">Hahella chejuensis KCTC 2396 (haheChej_KCTC_2396)</option>
            <option value="halMar1">Haloarcula marismortui ATCC 43049 (halMar1)</option>
            <option value="haloHalo1">Halobacterium sp. NRC-1 (haloHalo1)</option>
            <option value="haloWals1">Haloquadratum walsbyi DSM 16790 (haloWals1)</option>
            <option value="haloHalo_SL1">Halorhodospira halophila SL1 (haloHalo_SL1)</option>
            <option value="heliAcin_SHEEBA">Helicobacter acinonychis str. Sheeba (heliAcin_SHEEBA)</option>
            <option value="heliHepa1">Helicobacter hepaticus 06/18/2003 (heliHepa1)</option>
            
            <option value="heliHepa">Helicobacter hepaticus ATCC 51449 (heliHepa)</option>
            <option value="heliPylo_26695">Helicobacter pylori 26695 (heliPylo_26695)</option>
            <option value="heliPylo_26695_1">Helicobacter pylori 26695 08/07/1997 (heliPylo_26695_1)</option>
            <option value="heliPylo_HPAG1">Helicobacter pylori HPAG1 (heliPylo_HPAG1)</option>
            <option value="heliPylo_J99">Helicobacter pylori J99 (heliPylo_J99)</option>
            <option value="heliPylo_J99_1">Helicobacter pylori J99 01/29/1999 (heliPylo_J99_1)</option>
            <option value="hermArse">Herminiimonas arsenicoxydans (hermArse)</option>
            <option value="homIni14">Hominidae Oct. 1. 2006 (homIni14)</option>
            <option value="homIni13">Hominidae Apr. 24. 2006 (homIni13)</option>
            
            <option value="equCab1">Horse Jan. 2007 (equCab1)</option>
            <option value="hg18">Human Mar. 2006 (hg18)</option>
            <option value="hg17">Human May 2004 (hg17)</option>
            <option value="hg16">Human July 2003 (hg16)</option>
            <option value="hg15">Human Apr. 2003 (hg15)</option>
            <option value="hg13">Human Nov. 2002 (hg13)</option>
            <option value="hypeButy1">Hyperthermus butylicus DSM 5456 (hypeButy1)</option>
            <option value="hyphNept_ATCC15444">Hyphomonas neptunium ATCC 15444 (hyphNept_ATCC15444)</option>
            <option value="idioLoih_L2TR">Idiomarina loihiensis L2TR (idioLoih_L2TR)</option>
            
            <option value="venter1">J. Craig Venter Sep. 2007 (venter1)</option>
            <option value="jannCCS1">Jannaschia sp. CCS1 (jannCCS1)</option>
            <option value="lactPlan">Lactobacillus plantarum WCFS1 (lactPlan)</option>
            <option value="lactSali_UCC118">Lactobacillus salivarius UCC118 (lactSali_UCC118)</option>
            <option value="lactLact">Lactococcus lactis subsp. lactis Il1403 (lactLact)</option>
            <option value="petMar1">Lamprey Mar. 2007 (petMar1)</option>
            <option value="braFlo1">Lancelet Mar. 2006 (braFlo1)</option>
            <option value="lauRas13">Laurasiatheria Apr. 24. 2006 (lauRas13)</option>
            <option value="lawsIntr_PHE_MN1_00">Lawsonia intracellularis PHE/MN1-00 (lawsIntr_PHE_MN1_00)</option>
            
            <option value="legiPneu_PHILADELPHIA">Legionella pneumophila subsp. pneumophila str. Philadelphia 1 (legiPneu_PHILADELPHIA)</option>
            <option value="leifXyli_XYLI_CTCB0">Leifsonia xyli subsp. xyli str. CTCB07 (leifXyli_XYLI_CTCB0)</option>
            <option value="leptInte">Leptospira interrogans serovar Lai str. 56601 (leptInte)</option>
            <option value="leucMese_ATCC8293">Leuconostoc mesenteroides subsp. mesenteroides ATCC 8293 (leucMese_ATCC8293)</option>
            <option value="listInno">Listeria innocua Clip11262 (listInno)</option>
            <option value="anoCar1">Lizard Feb. 2007 (anoCar1)</option>
            <option value="magnMC1">Magnetococcus sp. MC-1 (magnMC1)</option>
            <option value="magnMagn_AMB_1">Magnetospirillum magneticum AMB-1 (magnMagn_AMB_1)</option>
            <option value="mannSucc_MBEL55E">Mannheimia succiniciproducens MBEL55E (mannSucc_MBEL55E)</option>
            
            <option value="mariMari_MCS10">Maricaulis maris MCS10 (mariMari_MCS10)</option>
            <option value="mariAqua_VT8">Marinobacter aquaeolei VT8 (mariAqua_VT8)</option>
            <option value="calJac1">Marmoset June 2007 (calJac1)</option>
            <option value="oryLat1">Medaka Apr. 2006 (oryLat1)</option>
            <option value="mesoFlor_L1">Mesoplasma florum L1 (mesoFlor_L1)</option>
            <option value="mesoLoti">Mesorhizobium loti MAFF303099 (mesoLoti)</option>
            <option value="metaSedu">Metallosphaera sedula DSM 5348 (metaSedu)</option>
            <option value="methSmit1">Methanobrevibacter smithii ATCC 35061 (methSmit1)</option>
            <option value="methJann1">Methanocaldococcus jannaschii DSM 2661 (methJann1)</option>
            
            <option value="methBurt2">Methanococcoides burtonii DSM 6242 (methBurt2)</option>
            <option value="methAeol1">Methanococcus aeolicus Nankai-3 (methAeol1)</option>
            <option value="methMari_C5_1">Methanococcus maripaludis C5 (methMari_C5_1)</option>
            <option value="methMari_C7">Methanococcus maripaludis C7 (methMari_C7)</option>
            <option value="metMar1">Methanococcus maripaludis S2 (metMar1)</option>
            <option value="methVann1">Methanococcus vannielii SB (methVann1)</option>
            <option value="methLabrZ_1">Methanocorpusculum labreanum Z (methLabrZ_1)</option>
            <option value="mculMari1">Methanoculleus marisnigri JR1 (mculMari1)</option>
            <option value="methKand1">Methanopyrus kandleri AV19 (methKand1)</option>
            
            <option value="methTherPT1">Methanosaeta thermophila PT (methTherPT1)</option>
            <option value="metAce1">Methanosarcina acetivorans C2A (metAce1)</option>
            <option value="methBark1">Methanosarcina barkeri str. Fusaro (methBark1)</option>
            <option value="methMaze1">Methanosarcina mazei Go1 (methMaze1)</option>
            <option value="methStad1">Methanosphaera stadtmanae DSM 3091 (methStad1)</option>
            <option value="methHung1">Methanospirillum hungatei JF-1 (methHung1)</option>
            <option value="methTher1">Methanothermobacter thermautotrophicus str. Delta H (methTher1)</option>
            <option value="methPetr_PM1">Methylibium petroleiphilum PM1 (methPetr_PM1)</option>
            <option value="methFlag_KT">Methylobacillus flagellatus KT (methFlag_KT)</option>
            
            <option value="methCaps_BATH">Methylococcus capsulatus str. Bath (methCaps_BATH)</option>
            <option value="moorTher_ATCC39073">Moorella thermoacetica ATCC 39073 (moorTher_ATCC39073)</option>
            <option value="mm9">Mouse July 2007 (mm9)</option>
            <option value="mm8">Mouse Feb. 2006 (mm8)</option>
            <option value="mm7">Mouse Aug. 2005 (mm7)</option>
            <option value="mm6">Mouse Mar. 2005 (mm6)</option>
            <option value="mm5">Mouse May 2004 (mm5)</option>
            <option value="mm4">Mouse Oct. 2003 (mm4)</option>
            <option value="mm3">Mouse Feb. 2003 (mm3)</option>
            
            <option value="mm2">Mouse Feb. 2002 (mm2)</option>
            <option value="mycoTube_H37RV">Mycobacterium tuberculosis H37Rv (mycoTube_H37RV)</option>
            <option value="mycoGeni">Mycoplasma genitalium G37 (mycoGeni)</option>
            <option value="myxoXant_DK_1622">Myxococcus xanthus DK 1622 (myxoXant_DK_1622)</option>
            <option value="nanEqu1">Nanoarchaeum equitans Kin4-M (nanEqu1)</option>
            <option value="natrPhar1">Natronomonas pharaonis DSM 2160 (natrPhar1)</option>
            <option value="neisGono_FA1090_1">Neisseria gonorrhoeae FA 1090 (neisGono_FA1090_1)</option>
            <option value="neisMeni_FAM18_1">Neisseria meningitidis FAM18 (neisMeni_FAM18_1)</option>
            <option value="neisMeni_MC58_1">Neisseria meningitidis MC58 (neisMeni_MC58_1)</option>
            
            <option value="neisMeni_Z2491_1">Neisseria meningitidis Z2491 (neisMeni_Z2491_1)</option>
            <option value="neorSenn_MIYAYAMA">Neorickettsia sennetsu str. Miyayama (neorSenn_MIYAYAMA)</option>
            <option value="nitrWino_NB_255">Nitrobacter winogradskyi Nb-255 (nitrWino_NB_255)</option>
            <option value="nitrOcea_ATCC19707">Nitrosococcus oceani ATCC 19707 (nitrOcea_ATCC19707)</option>
            <option value="nitrEuro">Nitrosomonas europaea ATCC 19718 (nitrEuro)</option>
            <option value="nitrMult_ATCC25196">Nitrosospira multiformis ATCC 25196 (nitrMult_ATCC25196)</option>
            <option value="nocaFarc_IFM10152">Nocardia farcinica IFM 10152 (nocaFarc_IFM10152)</option>
            <option value="nocaJS61">Nocardioides sp. JS614 (nocaJS61)</option>
            <option value="nonAfr13">Non-Afrotheria Apr. 24. 2006 (nonAfr13)</option>
            
            <option value="nostSp">Nostoc sp. PCC 7120 (nostSp)</option>
            <option value="novoArom_DSM12444">Novosphingobium aromaticivorans DSM 12444 (novoArom_DSM12444)</option>
            <option value="oceaIhey">Oceanobacillus iheyensis HTE831 (oceaIhey)</option>
            <option value="oenoOeni_PSU_1">Oenococcus oeni PSU-1 (oenoOeni_PSU_1)</option>
            <option value="onioYell_PHYTOPLASMA">Onion yellows phytoplasma OY-M (onioYell_PHYTOPLASMA)</option>
            <option value="monDom4">Opossum Jan. 2006 (monDom4)</option>
            <option value="monDom1">Opossum Oct. 2004 (monDom1)</option>
            <option value="ponAbe2">Orangutan July 2007 (ponAbe2)</option>
            <option value="orieTsut_BORYONG">Orientia tsutsugamushi str. Boryong (orieTsut_BORYONG)</option>
            
            <option value="falciparum">P. falciparum Plasmodium falciparum (falciparum)</option>
            <option value="priPac1">P. pacificus Feb. 2007 (priPac1)</option>
            <option value="paraDeni_PD1222">Paracoccus denitrificans PD1222 (paraDeni_PD1222)</option>
            <option value="pastMult">Pasteurella multocida subsp. multocida str. Pm70 (pastMult)</option>
            <option value="erwiCaro_ATROSEPTICA">Pectobacterium atrosepticum SCRI1043 (erwiCaro_ATROSEPTICA)</option>
            <option value="pediPent_ATCC25745">Pediococcus pentosaceus ATCC 25745 (pediPent_ATCC25745)</option>
            <option value="peloCarb">Pelobacter carbinolicus DSM 2380 (peloCarb)</option>
            <option value="peloLute_DSM273">Pelodictyon luteolum DSM 273 (peloLute_DSM273)</option>
            <option value="peloTher_SI">Pelotomaculum thermopropionicum SI (peloTher_SI)</option>
            
            <option value="photProf_SS9">Photobacterium profundum SS9 (photProf_SS9)</option>
            <option value="photLumi">Photorhabdus luminescens subsp. laumondii TTO1 (photLumi)</option>
            <option value="picrTorr1">Picrophilus torridus DSM 9790 (picrTorr1)</option>
            <option value="ornAna1">Platypus Mar. 2007 (ornAna1)</option>
            <option value="polaJS66">Polaromonas sp. JS666 (polaJS66)</option>
            <option value="polyQLWP">Polynucleobacter sp. QLW-P1DMWA-1 (polyQLWP)</option>
            <option value="porpGing_W83">Porphyromonas gingivalis W83 (porpGing_W83)</option>
            <option value="priMat13">Primate Apr. 24. 2006 (priMat13)</option>
            <option value="procMari_CCMP1375">Prochlorococcus marinus subsp. marinus str. CCMP1375 (procMari_CCMP1375)</option>
            
            <option value="propAcne_KPA171202">Propionibacterium acnes KPA171202 (propAcne_KPA171202)</option>
            <option value="pseuHalo_TAC125">Pseudoalteromonas haloplanktis TAC125 (pseuHalo_TAC125)</option>
            <option value="pseuAeru">Pseudomonas aeruginosa PAO1 (pseuAeru)</option>
            <option value="psycArct_273_4">Psychrobacter arcticus 273-4 (psycArct_273_4)</option>
            <option value="psycIngr_37">Psychromonas ingrahamii 37 (psycIngr_37)</option>
            <option value="pyrAer1">Pyrobaculum aerophilum str. IM2 (pyrAer1)</option>
            <option value="pyroArse1">Pyrobaculum arsenaticum DSM 13514 (pyroArse1)</option>
            <option value="pyroCali1">Pyrobaculum calidifontis JCM 11548 (pyroCali1)</option>
            <option value="pyroIsla1">Pyrobaculum islandicum DSM 4184 (pyroIsla1)</option>
            
            <option value="pyrAby1">Pyrococcus abyssi GE5 (pyrAby1)</option>
            <option value="pyrFur2">Pyrococcus furiosus DSM 3638 (pyrFur2)</option>
            <option value="pyrHor1">Pyrococcus horikoshii OT3 (pyrHor1)</option>
            <option value="oryCun1">Rabbit May 2005 (oryCun1)</option>
            <option value="ralsEutr_JMP134">Ralstonia eutropha JMP134 (ralsEutr_JMP134)</option>
            <option value="ralsSola">Ralstonia solanacearum GMI1000 (ralsSola)</option>
            <option value="rn4">Rat Nov. 2004 (rn4)</option>
            <option value="rn3">Rat June 2003 (rn3)</option>
            <option value="rn2">Rat Jan. 2003 (rn2)</option>
            
            <option value="rheMac2">Rhesus Jan. 2006 (rheMac2)</option>
            <option value="rhizEtli_CFN_42">Rhizobium etli CFN 42 (rhizEtli_CFN_42)</option>
            <option value="rhodSpha_2_4_1">Rhodobacter sphaeroides 2.4.1 (rhodSpha_2_4_1)</option>
            <option value="rhodRHA1">Rhodococcus sp. RHA1 (rhodRHA1)</option>
            <option value="pireSp">Rhodopirellula baltica SH 1 (pireSp)</option>
            <option value="rhodPalu_CGA009">Rhodopseudomonas palustris CGA009 (rhodPalu_CGA009)</option>
            <option value="rhodRubr_ATCC11170">Rhodospirillum rubrum ATCC 11170 (rhodRubr_ATCC11170)</option>
            <option value="rickBell_RML369_C">Rickettsia bellii RML369-C (rickBell_RML369_C)</option>
            <option value="rodEnt13">Rodent Apr. 24. 2006 (rodEnt13)</option>
            
            <option value="roseDeni_OCH_114">Roseobacter denitrificans OCh 114 (roseDeni_OCH_114)</option>
            <option value="rubrXyla_DSM9941">Rubrobacter xylanophilus DSM 9941 (rubrXyla_DSM9941)</option>
            <option value="sacCer1">S. cerevisiae Oct. 2003 (sacCer1)</option>
            <option value="strPur2">S. purpuratus Sep. 2006 (strPur2)</option>
            <option value="strPur1">S. purpuratus Apr. 2005 (strPur1)</option>
            <option value="sc1">SARS coronavirus Apr. 2003 (sc1)</option>
            <option value="saccDegr_2_40">Saccharophagus degradans 2-40 (saccDegr_2_40)</option>
            <option value="saccEryt_NRRL_2338">Saccharopolyspora erythraea NRRL 2338 (saccEryt_NRRL_2338)</option>
            <option value="saliRube_DSM13855">Salinibacter ruber DSM 13855 (saliRube_DSM13855)</option>
            
            <option value="saliTrop_CNB_440">Salinispora tropica CNB-440 (saliTrop_CNB_440)</option>
            <option value="salmEnte_PARATYPI_ATC">Salmonella enterica subsp. enterica serovar Paratyphi A str. ATCC 9150 (salmEnte_PARATYPI_ATC)</option>
            <option value="salmTyph">Salmonella enterica subsp. enterica serovar Typhi str. CT18 (salmTyph)</option>
            <option value="salmTyph_TY2">Salmonella enterica subsp. enterica serovar Typhi str. Ty2 (salmTyph_TY2)</option>
            <option value="shewAmaz">Shewanella amazonensis SB2B (shewAmaz)</option>
            <option value="shewBalt">Shewanella baltica OS155 (shewBalt)</option>
            <option value="shewDeni">Shewanella denitrificans OS217 (shewDeni)</option>
            <option value="shewFrig">Shewanella frigidimarina NCIMB 400 (shewFrig)</option>
            <option value="shewLoihPV4">Shewanella loihica PV-4 (shewLoihPV4)</option>
            
            <option value="shewOnei">Shewanella oneidensis MR-1 (shewOnei)</option>
            <option value="shewPutrCN32">Shewanella putrefaciens CN-32 (shewPutrCN32)</option>
            <option value="shewANA3">Shewanella sp. ANA-3 (shewANA3)</option>
            <option value="shewMR7">Shewanella sp. MR-7 (shewMR7)</option>
            <option value="shewMR4">Shewanella sp. MR-4 (shewMR4)</option>
            <option value="shewW318">Shewanella sp. W3-18-1 (shewW318)</option>
            <option value="shigFlex_2A">Shigella flexneri 2a str. 301 (shigFlex_2A)</option>
            <option value="siliPome_DSS_3">Silicibacter pomeroyi DSS-3 (siliPome_DSS_3)</option>
            <option value="sinoMeli">Sinorhizobium meliloti 1021 (sinoMeli)</option>
            
            <option value="choHof1">Sloth Feb. 2008 (choHof1)</option>
            <option value="sodaGlos_MORSITANS">Sodalis glossinidius str. 'morsitans' (sodaGlos_MORSITANS)</option>
            <option value="soliUsit_ELLIN6076">Solibacter usitatus Ellin6076 (soliUsit_ELLIN6076)</option>
            <option value="sphiAlas_RB2256">Sphingopyxis alaskensis RB2256 (sphiAlas_RB2256)</option>
            <option value="stapAure_MU50">Staphylococcus aureus subsp. aureus Mu50 (stapAure_MU50)</option>
            <option value="stapMari1">Staphylothermus marinus F1 (stapMari1)</option>
            <option value="gasAcu1">Stickleback Feb. 2006 (gasAcu1)</option>
            <option value="strePyog_M1_GAS">Streptococcus pyogenes M1 GAS (strePyog_M1_GAS)</option>
            <option value="streCoel">Streptomyces coelicolor A3(2) (streCoel)</option>
            
            <option value="sulfAcid1">Sulfolobus acidocaldarius DSM 639 (sulfAcid1)</option>
            <option value="sulSol1">Sulfolobus solfataricus P2 (sulSol1)</option>
            <option value="sulfToko1">Sulfolobus tokodaii str. 7 (sulfToko1)</option>
            <option value="symbTher_IAM14863">Symbiobacterium thermophilum IAM 14863 (symbTher_IAM14863)</option>
            <option value="syneSp_WH8102">Synechococcus sp. WH 8102 (syneSp_WH8102)</option>
            <option value="synePCC6">Synechocystis sp. PCC 6803 (synePCC6)</option>
            <option value="syntFuma_MPOB">Syntrophobacter fumaroxidans MPOB (syntFuma_MPOB)</option>
            <option value="syntWolf_GOETTINGEN">Syntrophomonas wolfei subsp. wolfei str. Goettingen (syntWolf_GOETTINGEN)</option>
            <option value="syntAcid_SB">Syntrophus aciditrophicus SB (syntAcid_SB)</option>
            
            <option value="triCas2">T. castaneum Sep. 2005 (triCas2)</option>
            <option value="echTel1">Tenrec July 2005 (echTel1)</option>
            <option value="tetNig1">Tetraodon Feb. 2004 (tetNig1)</option>
            <option value="therTeng">Thermoanaerobacter tengcongensis MB4 (therTeng)</option>
            <option value="therFusc_YX">Thermobifida fusca YX (therFusc_YX)</option>
            <option value="therKoda1">Thermococcus kodakarensis KOD1 (therKoda1)</option>
            <option value="therPend1">Thermofilum pendens Hrk 5 (therPend1)</option>
            <option value="therAcid1">Thermoplasma acidophilum DSM 1728 (therAcid1)</option>
            <option value="therVolc1">Thermoplasma volcanium GSS1 (therVolc1)</option>
            
            <option value="therElon">Thermosynechococcus elongatus BP-1 (therElon)</option>
            <option value="therMari">Thermotoga maritima MSB8 (therMari)</option>
            <option value="therPetr_RKU_1">Thermotoga petrophila RKU-1 (therPetr_RKU_1)</option>
            <option value="therTher_HB27">Thermus thermophilus HB27 (therTher_HB27)</option>
            <option value="therTher_HB8">Thermus thermophilus HB8 (therTher_HB8)</option>
            <option value="thioDeni_ATCC33889">Sulfurimonas denitrificans DSM 1251 (thioDeni_ATCC33889)</option>
            <option value="thioDeni_ATCC25259">Thiobacillus denitrificans ATCC 25259 (thioDeni_ATCC25259)</option>
            <option value="thioCrun_XCL_2">Thiomicrospira crunogena XCL-2 (thioCrun_XCL_2)</option>
            <option value="tupBel1">TreeShrew Dec. 2006 (tupBel1)</option>
            
            <option value="trepPall">Treponema pallidum subsp. pallidum str. Nichols (trepPall)</option>
            <option value="tricEryt_IMS101">Trichodesmium erythraeum IMS101 (tricEryt_IMS101)</option>
            <option value="tropWhip_TW08_27">Tropheryma whipplei TW08/27 (tropWhip_TW08_27)</option>
            <option value="ureaUrea">Ureaplasma parvum serovar 3 str. ATCC 700970 (ureaUrea)</option>
            <option value="vermEise_EF01_2">Verminephrobacter eiseniae EF01-2 (vermEise_EF01_2)</option>
            <option value="vibrChol_MO10_1">Vibrio cholerae MO10 09/17/2005 (vibrChol_MO10_1)</option>
            <option value="vibrChol1">Vibrio cholerae O1 El Tor 08/22/2000 (vibrChol1)</option>
            <option value="vibrChol_O395_1">Vibrio cholerae O395 09/17/2005 (vibrChol_O395_1)</option>
            <option value="vibrFisc_ES114_1">Vibrio fischeri ES114 02/11/2005 (vibrFisc_ES114_1)</option>
            
            <option value="vibrPara1">Vibrio parahaemolyticus 06/02/2000 (vibrPara1)</option>
            <option value="vibrVuln_CMCP6_1">Vibrio vulnificus CMCP6 09/23/2003 (vibrVuln_CMCP6_1)</option>
            <option value="vibrVuln_YJ016_1">Vibrio vulnificus YJ016 12/06/2003 (vibrVuln_YJ016_1)</option>
            <option value="wiggBrev">Wigglesworthia glossinidia endosymbiont of Glossina brevipalpis (wiggBrev)</option>
            <option value="wolbEndo_OF_DROSOPHIL">Wolbachia endosymbiont of Drosophila melanogaster (wolbEndo_OF_DROSOPHIL)</option>
            <option value="woliSucc">Wolinella succinogenes DSM 1740 (woliSucc)</option>
            <option value="xenTro2">X. tropicalis Aug. 2005 (xenTro2)</option>
            <option value="xenTro1">X. tropicalis Oct. 2004 (xenTro1)</option>
            <option value="xantCamp">Xanthomonas campestris pv. campestris str. ATCC 33913 (xantCamp)</option>
            
            <option value="xyleFast">Xylella fastidiosa 9a5c (xyleFast)</option>
            <option value="yersPest_CO92">Yersinia pestis CO92 (yersPest_CO92)</option>
            <option value="danRer5">Zebrafish July 2007 (danRer5)</option>
            <option value="danRer4">Zebrafish Mar. 2006 (danRer4)</option>
            <option value="danRer3">Zebrafish May 2005 (danRer3)</option>
            <option value="danRer2">Zebrafish June 2004 (danRer2)</option>
            <option value="danRer1">Zebrafish Nov. 2003 (danRer1)</option>
            <option value="zymoMobi_ZM4">Zymomonas mobilis subsp. mobilis ZM4 (zymoMobi_ZM4)</option>
            <option value="uncuMeth_RCI">uncultured methanogenic archaeon RC-I (uncuMeth_RCI)</option>
            
            <option value="?" selected>----- Additional Species Are Below -----</option>
            <option value="12997">Acaryochloris marina MBIC11017 (12997)</option>
            <option value="19259">Acholeplasma laidlawii PG-8A (19259)</option>
            <option value="15708">Acidovorax avenae subsp. citrulli AAC00-1 (15708)</option>
            <option value="13001">Acinetobacter baumannii (13001)</option>
            <option value="28921">Acinetobacter baumannii (28921)</option>
            <option value="17477">Acinetobacter baumannii ATCC 17978 (17477)</option>
            <option value="19135">Actinobacillus pleuropneumoniae serovar 3 str. JL03 (19135)</option>
            <option value="13370">Actinobacillus succinogenes 130Z (13370)</option>
            
            <option value="16723">Aeromonas salmonicida subsp. salmonicida A449 (16723)</option>
            <option value="283">Agrobacterium tumefaciens str. C58 (283)</option>
            <option value="13006">Alkaliphilus metalliredigens QYMF (13006)</option>
            <option value="16083">Alkaliphilus oremlandii OhILAs (16083)</option>
            <option value="17729">Anaeromyxobacter sp. Fw109-5 (17729)</option>
            <option value="336">Anaplasma phagocytophilum HZ (336)</option>
            <option value="16319">Arcobacter butzleri RM4018 (16319)</option>
            <option value="12512">Arthrobacter aurescens TC1 (12512)</option>
            <option value="13478">Aster yellows witches'-broom phytoplasma AYWB (13478)</option>
            
            <option value="13217">Azoarcus sp. BH72 (13217)</option>
            <option value="13403">Bacillus amyloliquefaciens FZB42 (13403)</option>
            <option value="10784">Bacillus anthracis str. 'Ames Ancestor' (10784)</option>
            <option value="10878">Bacillus anthracis str. Sterne (10878)</option>
            <option value="74">Bacillus cereus ATCC 10987 (74)</option>
            <option value="384">Bacillus cereus ATCC 14579 (384)</option>
            <option value="12468">Bacillus cereus E33L (12468)</option>
            <option value="13624">Bacillus cereus subsp. cytotoxis NVH 391-98 (13624)</option>
            <option value="13291">Bacillus clausii KSM-K16 (13291)</option>
            
            <option value="12388">Bacillus licheniformis ATCC 14580 (12388)</option>
            <option value="13082">Bacillus licheniformis ATCC 14580 (13082)</option>
            <option value="20391">Bacillus pumilus SAFR-032 (20391)</option>
            <option value="10877">Bacillus thuringiensis serovar konkukian str. 97-27 (10877)</option>
            <option value="18255">Bacillus thuringiensis str. Al Hakam (18255)</option>
            <option value="13623">Bacillus weihenstephanensis KBAB4 (13623)</option>
            <option value="46">Bacteroides fragilis NCTC 9343 (46)</option>
            <option value="13067">Bacteroides fragilis YCH46 (13067)</option>
            <option value="13378">Bacteroides vulgatus ATCC 8482 (13378)</option>
            
            <option value="16249">Bartonella bacilliformis KC583 (16249)</option>
            <option value="44">Bartonella quintana str. Toulouse (44)</option>
            <option value="28109">Bartonella tribocorum CIP 105476 (28109)</option>
            <option value="16321">Bifidobacterium adolescentis ATCC 15703 (16321)</option>
            <option value="25">Bordetella parapertussis 12822 (25)</option>
            <option value="26">Bordetella pertussis Tohama I (26)</option>
            <option value="28135">Bordetella petrii DSM 12804 (28135)</option>
            <option value="17057">Borrelia afzelii PKo (17057)</option>
            <option value="12554">Borrelia garinii PBi (12554)</option>
            
            <option value="16137">Bradyrhizobium sp. BTAi1 (16137)</option>
            <option value="19575">Bradyrhizobium sp. ORS278 (19575)</option>
            <option value="9619">Brucella abortus biovar 1 str. 9-941 (9619)</option>
            <option value="20243">Brucella canis ATCC 23365 (20243)</option>
            <option value="16203">Brucella melitensis biovar Abortus 2308 (16203)</option>
            <option value="12514">Brucella ovis ATCC 25840 (12514)</option>
            <option value="320">Brucella suis 1330 (320)</option>
            <option value="20371">Brucella suis ATCC 23445 (20371)</option>
            <option value="256">Buchnera aphidicola str. Bp (Baizongia pistaciae) (256)</option>
            
            <option value="16372">Buchnera aphidicola str. Cc (Cinara cedri) (16372)</option>
            <option value="312">Buchnera aphidicola str. Sg (Schizaphis graminum) (312)</option>
            <option value="17929">Burkholderia cenocepacia MC0-3 (17929)</option>
            <option value="13943">Burkholderia mallei NCTC 10229 (13943)</option>
            <option value="13946">Burkholderia mallei NCTC 10247 (13946)</option>
            <option value="13947">Burkholderia mallei SAVP1 (13947)</option>
            <option value="17407">Burkholderia multivorans ATCC 17616 (17407)</option>
            <option value="13954">Burkholderia pseudomallei 1710b (13954)</option>
            <option value="13953">Burkholderia pseudomallei 668 (13953)</option>
            
            <option value="178">Burkholderia pseudomallei K96243 (178)</option>
            <option value="17159">Campylobacter concisus 13826 (17159)</option>
            <option value="17161">Campylobacter curvus 525.92 (17161)</option>
            <option value="20083">Campylobacter hominis ATCC BAA-381 (20083)</option>
            <option value="17163">Campylobacter jejuni subsp. doylei 269.97 (17163)</option>
            <option value="17953">Campylobacter jejuni subsp. jejuni 81116 (17953)</option>
            <option value="13875">Candidatus Blochmannia pennsylvanicus str. BPEN (13875)</option>
            <option value="21047">Candidatus Desulforudis audaxviator MP104C (21047)</option>
            <option value="16525">Candidatus Korarchaeum cryptofilum OPF8 (16525)</option>
            
            <option value="16841">Candidatus Ruthia magnifica str. Cm (Calyptogena magnifica) (16841)</option>
            <option value="19617">Candidatus Sulcia muelleri GWSS (19617)</option>
            <option value="18267">Candidatus Vesicomyosocius okutanii HA (18267)</option>
            <option value="16306">Caulobacter sp. K31 (16306)</option>
            <option value="229">Chlamydia muridarum Nigg (229)</option>
            <option value="28583">Chlamydia trachomatis 434/Bu (28583)</option>
            <option value="13885">Chlamydia trachomatis A/HAR-13 (13885)</option>
            <option value="28585">Chlamydia trachomatis L2b/UCH-1/proctitis (28585)</option>
            <option value="355">Chlamydophila abortus S26/3 (355)</option>
            
            <option value="228">Chlamydophila caviae GPIC (228)</option>
            <option value="370">Chlamydophila felis Fe/C-56 (370)</option>
            <option value="247">Chlamydophila pneumoniae AR39 (247)</option>
            <option value="257">Chlamydophila pneumoniae J138 (257)</option>
            <option value="420">Chlamydophila pneumoniae TW-183 (420)</option>
            <option value="12609">Chlorobium phaeobacteroides DSM 266 (12609)</option>
            <option value="59">Chloroflexus aurantiacus J-10-fl (59)</option>
            <option value="12716">Citrobacter koseri ATCC BAA-895 (12716)</option>
            <option value="184">Clavibacter michiganensis subsp. sepedonicus (184)</option>
            
            <option value="77">Clostridium acetobutylicum ATCC 824 (77)</option>
            <option value="12637">Clostridium beijerinckii NCIMB 8052 (12637)</option>
            <option value="19517">Clostridium botulinum A str. ATCC 19397 (19517)</option>
            <option value="193">Clostridium botulinum A str. ATCC 3502 (193)</option>
            <option value="19521">Clostridium botulinum A str. Hall (19521)</option>
            <option value="28507">Clostridium botulinum A3 str. Loch Maree (28507)</option>
            <option value="28505">Clostridium botulinum B1 str. Okra (28505)</option>
            <option value="19519">Clostridium botulinum F str. Langeland (19519)</option>
            <option value="78">Clostridium difficile 630 (78)</option>
            
            <option value="19065">Clostridium kluyveri DSM 555 (19065)</option>
            <option value="16820">Clostridium novyi NT (16820)</option>
            <option value="304">Clostridium perfringens ATCC 13124 (304)</option>
            <option value="12521">Clostridium perfringens SM101 (12521)</option>
            <option value="79">Clostridium perfringens str. 13 (79)</option>
            <option value="16184">Clostridium phytofermentans ISDg (16184)</option>
            <option value="81">Clostridium tetani E88 (81)</option>
            <option value="314">Clostridium thermocellum ATCC 27405 (314)</option>
            <option value="87">Corynebacterium diphtheriae NCTC 13129 (87)</option>
            
            <option value="13760">Corynebacterium glutamicum ATCC 13032 (13760)</option>
            <option value="307">Corynebacterium glutamicum ATCC 13032 (307)</option>
            <option value="19193">Corynebacterium glutamicum R (19193)</option>
            <option value="13967">Corynebacterium jeikeium K411 (13967)</option>
            <option value="16721">Coxiella burnetii Dugway 5J108-111 (16721)</option>
            <option value="16791">Coxiella burnetii RSA 331 (16791)</option>
            <option value="15770">Dehalococcoides sp. BAV1 (15770)</option>
            <option value="15604">Dehalococcoides sp. CBDB1 (15604)</option>
            <option value="17413">Delftia acidovorans SPH-1 (17413)</option>
            
            <option value="18007">Desulfococcus oleovorans Hxd3 (18007)</option>
            <option value="329">Desulfovibrio desulfuricans G20 (329)</option>
            <option value="17227">Desulfovibrio vulgaris subsp. vulgaris DP4 (17227)</option>
            <option value="17417">Dinoroseobacter shibae DFL 12 (17417)</option>
            <option value="10694">Ehrlichia canis str. Jake (10694)</option>
            <option value="325">Ehrlichia chaffeensis str. Arkansas (325)</option>
            <option value="13356">Ehrlichia ruminantium str. Gardel (13356)</option>
            <option value="13355">Ehrlichia ruminantium str. Welgevonden (13355)</option>
            <option value="12720">Enterobacter sakazakii ATCC BAA-894 (12720)</option>
            
            <option value="16235">Escherichia coli 536 (16235)</option>
            <option value="18083">Escherichia coli C str. ATCC 8739 (18083)</option>
            <option value="20079">Escherichia coli DH10B (20079)</option>
            <option value="13960">Escherichia coli E24377A (13960)</option>
            <option value="13959">Escherichia coli HS (13959)</option>
            <option value="259">Escherichia coli O157:H7 EDL933 (259)</option>
            <option value="19469">Escherichia coli SECEC SMS-3-5 (19469)</option>
            <option value="16259">Escherichia coli UTI89 (16259)</option>
            <option value="16351">Escherichia coli W3110 (16351)</option>
            
            <option value="16719">Fervidobacterium nodosum Rt17-B1 (16719)</option>
            <option value="18981">Finegoldia magna ATCC 29328 (18981)</option>
            <option value="19979">Flavobacterium psychrophilum JIP02/86 (19979)</option>
            <option value="27853">Francisella philomiragia subsp. philomiragia ATCC 25017 (27853)</option>
            <option value="16421">Francisella tularensis subsp. holarctica (16421)</option>
            <option value="20197">Francisella tularensis subsp. holarctica FTA (20197)</option>
            <option value="17265">Francisella tularensis subsp. holarctica OSU18 (17265)</option>
            <option value="16088">Francisella tularensis subsp. novicida U112 (16088)</option>
            <option value="17375">Francisella tularensis subsp. tularensis FSC198 (17375)</option>
            
            <option value="18459">Francisella tularensis subsp. tularensis WY96-3418 (18459)</option>
            <option value="17403">Frankia alni ACN14a (17403)</option>
            <option value="13915">Frankia sp. EAN1pec (13915)</option>
            <option value="377">Gluconacetobacter diazotrophicus PAl 5 (377)</option>
            <option value="38">Haemophilus ducreyi 35000HP (38)</option>
            <option value="11752">Haemophilus influenzae 86-028NP (11752)</option>
            <option value="16400">Haemophilus influenzae PittEE (16400)</option>
            <option value="16401">Haemophilus influenzae PittGG (16401)</option>
            <option value="388">Haemophilus somnus 2336 (388)</option>
            
            <option value="106">Halobacterium salinarum R1 (106)</option>
            <option value="13427">Heliobacterium modesticaldum Ice1 (13427)</option>
            <option value="16523">Herpetosiphon aurantiacus ATCC 23779 (16523)</option>
            <option value="13914">Ignicoccus hospitalis KIN4/I (13914)</option>
            <option value="16549">Janthinobacterium sp. Marseille (16549)</option>
            <option value="10689">Kineococcus radiotolerans SRS30216 (10689)</option>
            <option value="31">Klebsiella pneumoniae subsp. pneumoniae MGH 78578 (31)</option>
            <option value="82">Lactobacillus acidophilus NCFM (82)</option>
            <option value="404">Lactobacillus brevis ATCC 367 (404)</option>
            
            <option value="402">Lactobacillus casei ATCC 334 (402)</option>
            <option value="16871">Lactobacillus delbrueckii subsp. bulgaricus ATCC 11842 (16871)</option>
            <option value="403">Lactobacillus delbrueckii subsp. bulgaricus ATCC BAA-365 (403)</option>
            <option value="84">Lactobacillus gasseri ATCC 33323 (84)</option>
            <option value="17811">Lactobacillus helveticus DPC 4571 (17811)</option>
            <option value="9638">Lactobacillus johnsonii NCC 533 (9638)</option>
            <option value="15766">Lactobacillus reuteri F275 (15766)</option>
            <option value="13435">Lactobacillus sakei subsp. sakei 23K (13435)</option>
            <option value="18797">Lactococcus lactis subsp. cremoris MG1363 (18797)</option>
            
            <option value="401">Lactococcus lactis subsp. cremoris SK11 (401)</option>
            <option value="17491">Legionella pneumophila str. Corby (17491)</option>
            <option value="13126">Legionella pneumophila str. Lens (13126)</option>
            <option value="13127">Legionella pneumophila str. Paris (13127)</option>
            <option value="16148">Leptospira borgpetersenii serovar Hardjo-bovis JB197 (16148)</option>
            <option value="16146">Leptospira borgpetersenii serovar Hardjo-bovis L550 (16146)</option>
            <option value="10687">Leptospira interrogans serovar Copenhageni str. Fiocruz L1-130 (10687)</option>
            <option value="20039">Leptothrix cholodnii SP-6 (20039)</option>
            <option value="16062">Leuconostoc citreum KM20 (16062)</option>
            
            <option value="276">Listeria monocytogenes EGD-e (276)</option>
            <option value="85">Listeria monocytogenes str. 4b F2365 (85)</option>
            <option value="13443">Listeria welshimeri serovar 6b str. SLCC5334 (13443)</option>
            <option value="19619">Lysinibacillus sphaericus C3-41 (19619)</option>
            <option value="17445">Marinomonas sp. MWYL1 (17445)</option>
            <option value="10690">Mesorhizobium sp. BNC1 (10690)</option>
            <option value="19639">Methanococcus maripaludis C6 (19639)</option>
            <option value="18637">Methylobacterium extorquens PA1 (18637)</option>
            <option value="18817">Methylobacterium radiotolerans JCM 2831 (18817)</option>
            
            <option value="18809">Methylobacterium sp. 4-46 (18809)</option>
            <option value="27835">Microcystis aeruginosa NIES-843 (27835)</option>
            <option value="15691">Mycobacterium abscessus (15691)</option>
            <option value="88">Mycobacterium avium 104 (88)</option>
            <option value="91">Mycobacterium avium subsp. paratuberculosis K-10 (91)</option>
            <option value="89">Mycobacterium bovis AF2122/97 (89)</option>
            <option value="18059">Mycobacterium bovis BCG str. Pasteur 1173P2 (18059)</option>
            <option value="15760">Mycobacterium gilvum PYR-GCK (15760)</option>
            <option value="90">Mycobacterium leprae TN (90)</option>
            
            <option value="92">Mycobacterium smegmatis str. MC2 155 (92)</option>
            <option value="16079">Mycobacterium sp. JLS (16079)</option>
            <option value="16081">Mycobacterium sp. KMS (16081)</option>
            <option value="15762">Mycobacterium sp. MCS (15762)</option>
            <option value="223">Mycobacterium tuberculosis CDC1551 (223)</option>
            <option value="15642">Mycobacterium tuberculosis F11 (15642)</option>
            <option value="18883">Mycobacterium tuberculosis H37Ra (18883)</option>
            <option value="16230">Mycobacterium ulcerans Agy99 (16230)</option>
            <option value="15761">Mycobacterium vanbaalenii PYR-1 (15761)</option>
            
            <option value="16095">Mycoplasma agalactiae PG2 (16095)</option>
            <option value="16208">Mycoplasma capricolum subsp. capricolum ATCC 27343 (16208)</option>
            <option value="409">Mycoplasma gallisepticum R (409)</option>
            <option value="13120">Mycoplasma hyopneumoniae 232 (13120)</option>
            <option value="10639">Mycoplasma hyopneumoniae 7448 (10639)</option>
            <option value="10675">Mycoplasma hyopneumoniae J (10675)</option>
            <option value="10697">Mycoplasma mobile 163K (10697)</option>
            <option value="10616">Mycoplasma mycoides subsp. mycoides SC str. PG1 (10616)</option>
            <option value="176">Mycoplasma penetrans HF-2 (176)</option>
            
            <option value="99">Mycoplasma pneumoniae M129 (99)</option>
            <option value="100">Mycoplasma pulmonis UAB CTIP (100)</option>
            <option value="10676">Mycoplasma synoviae 53 (10676)</option>
            <option value="16393">Neisseria meningitidis 053442 (16393)</option>
            <option value="18963">Nitratiruptor sp. SB155-2 (18963)</option>
            <option value="13473">Nitrobacter hamburgensis X14 (13473)</option>
            <option value="13913">Nitrosomonas eutropha C91 (13913)</option>
            <option value="19265">Nitrosopumilus maritimus SCM1 (19265)</option>
            <option value="19485">Ochrobactrum anthropi ATCC 49188 (19485)</option>
            
            <option value="13485">Parabacteroides distasonis ATCC 8503 (13485)</option>
            <option value="17639">Parvibaculum lavamentivorans DS-1 (17639)</option>
            <option value="13384">Pelobacter propionicus DSM 2379 (13384)</option>
            <option value="17679">Petrotoga mobilis SJ95 (17679)</option>
            <option value="13418">Polaromonas naphthalenivorans CJ2 (13418)</option>
            <option value="13548">Prochlorococcus marinus str. AS9601 (13548)</option>
            <option value="13551">Prochlorococcus marinus str. MIT 9211 (13551)</option>
            <option value="18633">Prochlorococcus marinus str. MIT 9215 (18633)</option>
            <option value="15746">Prochlorococcus marinus str. MIT 9301 (15746)</option>
            
            <option value="13496">Prochlorococcus marinus str. MIT 9303 (13496)</option>
            <option value="13910">Prochlorococcus marinus str. MIT 9312 (13910)</option>
            <option value="220">Prochlorococcus marinus str. MIT 9313 (220)</option>
            <option value="13617">Prochlorococcus marinus str. MIT 9515 (13617)</option>
            <option value="15660">Prochlorococcus marinus str. NATL1A (15660)</option>
            <option value="13911">Prochlorococcus marinus str. NATL2A (13911)</option>
            <option value="213">Prochlorococcus marinus subsp. pastoris str. CCMP1986 (213)</option>
            <option value="12607">Prosthecochloris vibrioformis DSM 265 (12607)</option>
            <option value="13454">Pseudoalteromonas atlantica T6c (13454)</option>
            
            <option value="16720">Pseudomonas aeruginosa PA7 (16720)</option>
            <option value="386">Pseudomonas aeruginosa UCBPP-PA14 (386)</option>
            <option value="16800">Pseudomonas entomophila L48 (16800)</option>
            <option value="327">Pseudomonas fluorescens Pf-5 (327)</option>
            <option value="12">Pseudomonas fluorescens PfO-1 (12)</option>
            <option value="17457">Pseudomonas mendocina ymp (17457)</option>
            <option value="13909">Pseudomonas putida F1 (13909)</option>
            <option value="17629">Pseudomonas putida GB-1 (17629)</option>
            <option value="267">Pseudomonas putida KT2440 (267)</option>
            
            <option value="17053">Pseudomonas putida W619 (17053)</option>
            <option value="16817">Pseudomonas stutzeri A1501 (16817)</option>
            <option value="12416">Pseudomonas syringae pv. phaseolicola 1448A (12416)</option>
            <option value="323">Pseudomonas syringae pv. syringae B728a (323)</option>
            <option value="359">Pseudomonas syringae pv. tomato str. DC3000 (359)</option>
            <option value="13920">Psychrobacter cryohalolentis K5 (13920)</option>
            <option value="15759">Psychrobacter sp. PRwf-1 (15759)</option>
            <option value="13603">Ralstonia eutropha H16 (13603)</option>
            <option value="250">Ralstonia metallidurans CH34 (250)</option>
            
            <option value="19227">Renibacterium salmoninarum ATCC 33209 (19227)</option>
            <option value="344">Rhizobium leguminosarum bv. viciae 3841 (344)</option>
            <option value="15755">Rhodobacter sphaeroides ATCC 17025 (15755)</option>
            <option value="15754">Rhodobacter sphaeroides ATCC 17029 (15754)</option>
            <option value="13908">Rhodoferax ferrireducens T118 (13908)</option>
            <option value="15751">Rhodopseudomonas palustris BisA53 (15751)</option>
            <option value="15750">Rhodopseudomonas palustris BisB18 (15750)</option>
            <option value="15749">Rhodopseudomonas palustris BisB5 (15749)</option>
            <option value="15747">Rhodopseudomonas palustris HaA2 (15747)</option>
            
            <option value="12953">Rickettsia akari str. Hartford (12953)</option>
            <option value="17237">Rickettsia bellii OSU 85-389 (17237)</option>
            <option value="12952">Rickettsia canadensis str. McKiel (12952)</option>
            <option value="42">Rickettsia conorii str. Malish 7 (42)</option>
            <option value="13884">Rickettsia felis URRWXCal2 (13884)</option>
            <option value="18271">Rickettsia massiliae MTU5 (18271)</option>
            <option value="43">Rickettsia prowazekii str. Madrid E (43)</option>
            <option value="9636">Rickettsia rickettsii str. 'Sheila Smith' (9636)</option>
            <option value="19943">Rickettsia rickettsii str. Iowa (19943)</option>
            
            <option value="10679">Rickettsia typhi str. Wilmington (10679)</option>
            <option value="13462">Roseiflexus castenholzii DSM 13941 (13462)</option>
            <option value="16190">Roseiflexus sp. RS-1 (16190)</option>
            <option value="17109">Salinispora arenicola CNS-205 (17109)</option>
            <option value="13030">Salmonella enterica subsp. arizonae serovar 62:z4,z23:-- (13030)</option>
            <option value="9618">Salmonella enterica subsp. enterica serovar Choleraesuis str. SC-B67 (9618)</option>
            <option value="27803">Salmonella enterica subsp. enterica serovar Paratyphi B str. SPB7 (27803)</option>
            <option value="241">Salmonella typhimurium LT2 (241)</option>
            <option value="17459">Serratia proteamaculans 568 (17459)</option>
            
            <option value="17643">Shewanella baltica OS185 (17643)</option>
            <option value="13389">Shewanella baltica OS195 (13389)</option>
            <option value="20241">Shewanella halifaxensis HAW-EB4 (20241)</option>
            <option value="17415">Shewanella pealeana ATCC 700345 (17415)</option>
            <option value="18789">Shewanella sediminis HAW-EB3 (18789)</option>
            <option value="17455">Shewanella woodyi ATCC 51908 (17455)</option>
            <option value="13146">Shigella boydii Sb227 (13146)</option>
            <option value="13145">Shigella dysenteriae Sd197 (13145)</option>
            <option value="408">Shigella flexneri 2a str. 2457T (408)</option>
            
            <option value="16375">Shigella flexneri 5 str. 8401 (16375)</option>
            <option value="13151">Shigella sonnei Ss046 (13151)</option>
            <option value="13040">Silicibacter sp. TM1040 (13040)</option>
            <option value="16304">Sinorhizobium medicae WSM419 (16304)</option>
            <option value="28111">Sorangium cellulosum 'So ce 56' (28111)</option>
            <option value="17343">Sphingomonas wittichii RW1 (17343)</option>
            <option value="63">Staphylococcus aureus RF122 (63)</option>
            <option value="238">Staphylococcus aureus subsp. aureus COL (238)</option>
            <option value="15758">Staphylococcus aureus subsp. aureus JH1 (15758)</option>
            
            <option value="15757">Staphylococcus aureus subsp. aureus JH9 (15757)</option>
            <option value="265">Staphylococcus aureus subsp. aureus MRSA252 (265)</option>
            <option value="266">Staphylococcus aureus subsp. aureus MSSA476 (266)</option>
            <option value="306">Staphylococcus aureus subsp. aureus MW2 (306)</option>
            <option value="18509">Staphylococcus aureus subsp. aureus Mu3 (18509)</option>
            <option value="264">Staphylococcus aureus subsp. aureus N315 (264)</option>
            <option value="237">Staphylococcus aureus subsp. aureus NCTC 8325 (237)</option>
            <option value="16313">Staphylococcus aureus subsp. aureus USA300 (16313)</option>
            <option value="19489">Staphylococcus aureus subsp. aureus USA300_TCH1516 (19489)</option>
            
            <option value="18801">Staphylococcus aureus subsp. aureus str. Newman (18801)</option>
            <option value="279">Staphylococcus epidermidis ATCC 12228 (279)</option>
            <option value="64">Staphylococcus epidermidis RP62A (64)</option>
            <option value="12508">Staphylococcus haemolyticus JCSC1435 (12508)</option>
            <option value="15596">Staphylococcus saprophyticus subsp. saprophyticus ATCC 15305 (15596)</option>
            <option value="330">Streptococcus agalactiae 2603V/R (330)</option>
            <option value="326">Streptococcus agalactiae A909 (326)</option>
            <option value="334">Streptococcus agalactiae NEM316 (334)</option>
            <option value="66">Streptococcus gordonii str. Challis substr. CH1 (66)</option>
            
            <option value="333">Streptococcus mutans UA159 (333)</option>
            <option value="16374">Streptococcus pneumoniae D39 (16374)</option>
            <option value="28035">Streptococcus pneumoniae Hungary19A-6 (28035)</option>
            <option value="278">Streptococcus pneumoniae R6 (278)</option>
            <option value="277">Streptococcus pneumoniae TIGR4 (277)</option>
            <option value="16364">Streptococcus pyogenes MGAS10270 (16364)</option>
            <option value="12469">Streptococcus pyogenes MGAS10394 (12469)</option>
            <option value="16366">Streptococcus pyogenes MGAS10750 (16366)</option>
            <option value="16365">Streptococcus pyogenes MGAS2096 (16365)</option>
            
            <option value="311">Streptococcus pyogenes MGAS315 (311)</option>
            <option value="13888">Streptococcus pyogenes MGAS5005 (13888)</option>
            <option value="13887">Streptococcus pyogenes MGAS6180 (13887)</option>
            <option value="286">Streptococcus pyogenes MGAS8232 (286)</option>
            <option value="16363">Streptococcus pyogenes MGAS9429 (16363)</option>
            <option value="301">Streptococcus pyogenes SSI-1 (301)</option>
            <option value="270">Streptococcus pyogenes str. Manfredo (270)</option>
            <option value="13942">Streptococcus sanguinis SK36 (13942)</option>
            <option value="17153">Streptococcus suis 05ZYH33 (17153)</option>
            
            <option value="17155">Streptococcus suis 98HAH33 (17155)</option>
            <option value="13163">Streptococcus thermophilus CNRZ1066 (13163)</option>
            <option value="13773">Streptococcus thermophilus LMD-9 (13773)</option>
            <option value="13162">Streptococcus thermophilus LMG 18311 (13162)</option>
            <option value="189">Streptomyces avermitilis MA-4680 (189)</option>
            <option value="18965">Sulfurovum sp. NBC37-1 (18965)</option>
            <option value="13282">Synechococcus elongatus PCC 6301 (13282)</option>
            <option value="10645">Synechococcus elongatus PCC 7942 (10645)</option>
            <option value="12530">Synechococcus sp. CC9311 (12530)</option>
            
            <option value="13643">Synechococcus sp. CC9605 (13643)</option>
            <option value="13655">Synechococcus sp. CC9902 (13655)</option>
            <option value="16252">Synechococcus sp. JA-2-3B'a(2-13) (16252)</option>
            <option value="16251">Synechococcus sp. JA-3-3Ab (16251)</option>
            <option value="28247">Synechococcus sp. PCC 7002 (28247)</option>
            <option value="13654">Synechococcus sp. RCC307 (13654)</option>
            <option value="13642">Synechococcus sp. WH 7803 (13642)</option>
            <option value="13901">Thermoanaerobacter pseudethanolicus ATCC 33223 (13901)</option>
            <option value="16394">Thermoanaerobacter sp. X514 (16394)</option>
            
            <option value="17249">Thermosipho melanesiensis BI429 (17249)</option>
            <option value="15644">Thermotoga lettingae TMO (15644)</option>
            <option value="19543">Thermotoga sp. RQ2 (19543)</option>
            <option value="4">Treponema denticola ATCC 35405 (4)</option>
            <option value="95">Tropheryma whipplei str. Twist (95)</option>
            <option value="19087">Ureaplasma parvum serovar 3 str. ATCC 27815 (19087)</option>
            <option value="19857">Vibrio harveyi ATCC BAA-1116 (19857)</option>
            <option value="12475">Wolbachia endosymbiont strain TRS of Brugia malayi (12475)</option>
            <option value="15756">Xanthobacter autotrophicus Py2 (15756)</option>
            
            <option value="297">Xanthomonas axonopodis pv. citri str. 306 (297)</option>
            <option value="15">Xanthomonas campestris pv. campestris str. 8004 (15)</option>
            <option value="13649">Xanthomonas campestris pv. vesicatoria str. 85-10 (13649)</option>
            <option value="12931">Xanthomonas oryzae pv. oryzae KACC10331 (12931)</option>
            <option value="16297">Xanthomonas oryzae pv. oryzae MAFF 311018 (16297)</option>
            <option value="17823">Xylella fastidiosa M12 (17823)</option>
            <option value="285">Xylella fastidiosa Temecula1 (285)</option>
            <option value="190">Yersinia enterocolitica subsp. enterocolitica 8081 (190)</option>
            <option value="16067">Yersinia pestis Angola (16067)</option>
            
            <option value="16645">Yersinia pestis Antiqua (16645)</option>
            <option value="288">Yersinia pestis KIM (288)</option>
            <option value="16646">Yersinia pestis Nepal516 (16646)</option>
            <option value="16700">Yersinia pestis Pestoides F (16700)</option>
            <option value="10638">Yersinia pestis biovar Microtus str. 91001 (10638)</option>
            <option value="16070">Yersinia pseudotuberculosis IP 31758 (16070)</option>
            <option value="12950">Yersinia pseudotuberculosis IP 32953 (12950)</option>
            <option value="28743">Yersinia pseudotuberculosis YPIII (28743)</option>
        </select></div>
        <div style="clear: both"></div>
      </div>
      <div class="form-row">
        <input type="submit" class="primary-button" name="create_dataset" value="Create Dataset">
      </div>
    </form>
  </div>
</div>

#!/bin/env python
# make the gsea loc files needed for the rgGSEA tool from a directory
# containing gmt and chip files downloaded from the gsea site
# Copyright ross lazarus feb 2012 
# all rights reserved
# licensed under the LGPL

import os,sys,glob,time

notes = """

   <table name="gseaChip" comment_char="#">
       <columns>value, name, path</columns>
       <file path="tool-data/gseaChip_%s.loc" />
   </table>
   <table name="gseaGMT" comment_char="#">
       <columns>value, name, path</columns>
       <file path="tool-data/gseaGMTsymbols%s.loc" />
   </table>

"""

def timenow():
    """return current time as a string
    """
    return time.strftime('%d/%m/%Y %H:%M:%S', time.localtime(time.time()))

def makeLoc(paths=[],head=[],outpath='gseaChip.loc',):
    """
    write a 3 column loc file - name, value, path from a glob list
    """
    paths.sort()
    loc = [[os.path.basename(x),x] for x in paths]
    loc = [[os.path.splitext(x[0])[0],os.path.splitext(x[0])[0],x[1]] for x in loc]
    loc = ['\t'.join(x) for x in loc]
    loc.sort()
    f = open(outpath,'w')
    f.write('\n'.join(head))
    f.write('\n')
    f.write('\n'.join(loc))
    f.write('\n')
    f.close()

"""
AgoodchoiceC2_c3_c5_entrez_all.gmt   Clontech_BD_Atlas.chip                          MOE430B.chip
AgoodchoiceC2_c3_c5_orig_all.gmt     CNMCMuscleChip.chip                             MoEx_1_0_st.chip
AgoodchoiceC2_c3_c5_symbols_all.gmt  CodeLink_Human_Whole_Genome.chip                MoGene_1_0_st.chip
APPLERA_ABI1700.chip                 CodeLink_UniSet_Human_20K_I_Bioarray.chip       MoGene_1_1_st.chip
ATH1_121501.chip                     CodeLink_UniSet_Human_I_Bioarray.chip           Mouse430_2.chip
AtlasMouse1.2.chip                   CodeLink_UniSet_Human_II_Bioarray.chip          Mouse430A_2.chip
AtlasRat1.2.chip                     CodeLink_UniSet_Rat_I_Bioarray.chip             msigdb.v3.1.entrez.gmt
BIAO.chip                            DrosGenome1.chip                                msigdb_v3.1_files_to_download_locally
Bovine.chip                          Drosophila_2.chip                               msigdb.v3.1.orig.gmt
c1.all.v3.1.entrez.gmt               G4110A.chip                                     msigdb.v3.1.symbols.gmt
c1.all.v3.1.orig.gmt                 G4110Av2.chip                                   msigdb_v3.1.xml
c1.all.v3.1.symbols.gmt              GENE_SYMBOL.chip                                Mu11KsubA.chip
c2.all.v3.1.entrez.gmt               GenosysCytokineV2.chip                          Mu11KsubB.chip
c2.all.v3.1.orig.gmt                 gseaChip3.1.loc                                 Mu19KsubA.chip
c2.all.v3.1.symbols.gmt              gseaGMTsymbols_3.1.loc                          Mu19KsubB.chip
c2.cgp.v3.1.entrez.gmt               HC_G110.chip                                    Mu19KsubC.chip
c2.cgp.v3.1.orig.gmt                 HG_Focus.chip                                   MWG_Human_30K_A.chip
c2.cgp.v3.1.symbols.gmt              HG_U133A_2.chip                                 MWG_Human_30K_B.chip
c2.cp.biocarta.v3.1.entrez.gmt       HG_U133AAOFAV2.chip                             Netherland_cancer_institute_operon_human_35k.chip
c2.cp.biocarta.v3.1.orig.gmt         HG_U133A.chip                                   Netherland_cancer_institute_operon_mouse_FOOk.chip
c2.cp.biocarta.v3.1.symbols.gmt      HG_U133B.chip                                   NIA15k.chip
c2.cp.kegg.v3.1.entrez.gmt           HG_U133_Plus_2.chip                             OPERON_HUMANv2.chip
c2.cp.kegg.v3.1.orig.gmt             HG_U95Av2.chip                                  OPERON_HUMANv3.chip
c2.cp.kegg.v3.1.symbols.gmt          HG_U95B.chip                                    Ortholog_SEQ_ACCESSION_MOUSE.chip
c2.cp.reactome.v3.1.entrez.gmt       HG_U95C.chip                                    RAE230A.chip
c2.cp.reactome.v3.1.orig.gmt         HG_U95D.chip                                    RAE230B.chip
c2.cp.reactome.v3.1.symbols.gmt      HG_U95E.chip                                    Rat230_2.chip
c2.cp.v3.1.entrez.gmt                HPCGGCompugenAnnotations.chip                   RefSeq_human.chip
c2.cp.v3.1.orig.gmt                  HT_HG_U133A.chip                                RefSeq_NP_Human.chip
c2.cp.v3.1.symbols.gmt               HT_HG_U133A_EA.chip                             RefSeq_NP_Mouse.chip
c3.all.v3.1.entrez.gmt               Hu35KsubA.chip                                  RefSeq_NP_Rat.chip
c3.all.v3.1.orig.gmt                 Hu35KsubB.chip                                  Research_Genetics.chip
c3.all.v3.1.symbols.gmt              Hu35KsubC.chip                                  RG_U34A.chip
c3.mir.v3.1.entrez.gmt               Hu35KsubD.chip                                  RG_U34B.chip
c3.mir.v3.1.orig.gmt                 HU6800.chip                                     RG_U34C.chip
c3.mir.v3.1.symbols.gmt              HuEx_1_0_STv2.chip                              RN_U34.chip
c3.tft.v3.1.entrez.gmt               HuGene_1_0_st.chip                              Rosetta50K.chip
c3.tft.v3.1.orig.gmt                 Illimina_Mus6_v1_1.chip                         Rosetta.chip
c3.tft.v3.1.symbols.gmt              Illimuna_Mus6_v1.chip                           RT_U34.chip
c4.all.v3.1.entrez.gmt               Illumina_Hum6_v1.chip                           RZPD_Human_Ensembl1.1.chip
c4.all.v3.1.orig.gmt                 Illumina_Hum6_v2.chip                           RZPD_Human_ORF_Clones_Gateway.chip
c4.all.v3.1.symbols.gmt              Illumina_Human.chip                             RZPD_Human_Unigene3.1.chip
c4.cgn.v3.1.entrez.gmt               Illumina_HumRef8_v1.chip                        Seq_Accession.chip
c4.cgn.v3.1.orig.gmt                 Illumina_HumRef8_v2.chip                        Stanford.chip
c4.cgn.v3.1.symbols.gmt              Illumina_Mus6_v2.chip                           Stanford_Source_Accessions.chip
c4.cm.v3.1.entrez.gmt                Illumina_MusRef8_v1_1.chip                      TIGR_31K_Human_Set.chip
c4.cm.v3.1.orig.gmt                  Illumina_MusRef8_v1.chip                        TIGR_40K_Human_Set.chip
c4.cm.v3.1.symbols.gmt               Illumina_RatRef12_v1.chip                       TRC.chip
c5.all.v3.1.entrez.gmt               ilmn_HumanHT_12_V3_0_R3_11283641_A.chip         TRC_DB.chip
c5.all.v3.1.orig.gmt                 ilmn_HumanHT_12_V4_0_R1_15002873_B.chip         TRC_DB_v1.chip
c5.all.v3.1.symbols.gmt              ilmn_HumanRef_8_V2_0_R4_11223162_A.chip         U133_X3P.chip
c5.bp.v3.1.entrez.gmt                ilmn_HUMANREF_8_V3_0_R1_11282963_A_WGDASL.chip  UCLA_NIH_33K.chip
c5.bp.v3.1.orig.gmt                  ilmn_HumanRef_8_V3_0_R3_11282963_A.chip         Zebrafish.chip
c5.bp.v3.1.symbols.gmt  
"""
import subprocess

def makeRoss():
    for kind in ['orig','symbols','entrez']:
        outf = 'Abetterchoice_nocgp_c2_c3_c5_%s_all.gmt' % kind
        o = open(outf,'w')
        s = 'cat c2.cp.biocarta.v3.1.%s.gmt c2.cp.kegg.v3.1.%s.gmt c2.cp.reactome.v3.1.%s.gmt c3.all.v3.1.%s.gmt c5.all.v3.1.%s.gmt' \
            % (kind,kind,kind,kind,kind)
        cl = s.split(' ')
        print 'running',cl
        p = subprocess.check_call(cl,shell=False,stdout=o)
        o.close()
        outf = 'Agoodchoice_c2_c3_c5_%s_all.gmt' % kind
        o = open(outf,'w')
        s = 'cat c2.all.v3.1.%s.gmt c3.all.v3.1.%s.gmt c5.all.v3.1.%s.gmt' \
            % (kind,kind,kind)
        cl = s.split(' ')
        print 'running',cl
        p = subprocess.check_call(cl,shell=False,stdout=o)
        o.close()
        

def main():
    if len(sys.argv) >= 1:
        usedir = os.path.abspath(sys.argv[1])
        vers = sys.argv[2] or '3.1'
        print 'Using supplied path',usedir,'and vers',vers
    else: # default at BakerIDI
        usedir = '/data/genomes/gsea'
        vers = '3.1'
        print 'Using default path',usedir,'and vers',vers
    assert os.path.isdir(usedir),'## unable to open %s - please pass the path to a directory containing all gsea chip/gmt downloaded from ftp://gseaftp.broadinstitute.org/pub/gsea/annotations on the command line' % usedir
    progName = os.path.basename(sys.argv[0])
    h = ['# generated by %s at %s from path = %s' % (progName,timenow(),usedir),'# loc file for the rgGSEA tool pointing to files from ftp://gseaftp.broadinstitute.org/pub/gsea/annotations','# name value path']
    makeRoss()
    chips = glob.glob(os.path.join(usedir,'*.chip'))
    makeLoc(paths=chips,head=h,outpath=os.path.join(usedir,'gseaChip%s.loc' % vers))
    for kind in ['orig','symbols','entrez']:
        gmt = glob.glob(os.path.join(usedir,'*.gmt'))
        gmt = [x for x in gmt if x.find(kind) <> -1]
        makeLoc(paths=gmt,head=h,outpath=os.path.join(usedir,'gseaGMT%s_%s.loc' % (kind,vers)))
    print '## %s done. copy the new .loc files in %s to your galaxy tool-data directory, add them to your tool_data_tables.xml file and restart Galaxy' % (progName,usedir)
    print '## something like:'
    print notes % (vers,vers)
    print '## should do for tool_data_tables.xml'
if __name__=="__main__":
    main()

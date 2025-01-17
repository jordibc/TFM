#!/usr/bin/python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
import re
import os
from ko_functions2 import get_ko_list, find_basal, check_unmapped

# @dataclass
# class Eggnog_orf(object):

#     """
#     Dataclass to store eggnog's attributes corresponding to one orf
#     """

#     query: str
#     og: str 
#     kingdom: str 
#     description: str # = field(repr=False)
#     preferred_name:	str
#     #GOs: str	
#     kegg_ko: list
#     kegg_pathway: str
#     #KEGG_Module: str	
#     #contig: str #= field(init=False) 
#     abundance: float

#     def __str__(self):

#         """
#         Instance method to define the print format of the instance
#         """

#         row_list = [self.query, self.seed_ortholog, self.eggnog_ogs, self.max_annot_lvl, self.kegg_ko, self.kegg_pathway, self.contig]
#         s = '\t'.join([str(item) for item in row_list])
        
#         return s
    
            
class Eggnog_sample(object):

    """
    Class to store all rows from an eggnog-mapper file. 
    Each row is a eggnog_orf instance
    """

    option_unit = None # the option unit as given in the arguments
    calc_unit = None # the unit we use for calculations
    sample_list = None
    

    def __init__(self, filename: str, total_sample:float, samplename = None, remove_euk = False) -> None:
        #self.rows = []
        self.filename = filename
        self.remove_euk = remove_euk
        if samplename == None :
            self.samplename = self.define_samplename() # function to extract samplename from filename
        else: 
            self.samplename = samplename
        
        self.og_abundance = {}
        self.ko_abundance = {}
        self.total = total_sample
        self.mapped_og = 0
        self.mapped_ko = 0
        self.global_ko_list = []

        # self.query_list = []
        # self.query_dict = {}
        # self.all_dict = {}

    @classmethod
    def init_unit(cls, given_unit):

        # dictionary to transform argument options into coverm units names 
        unit_dict ={'rpkm': 'RPKM', 'tpm': 'TPM', 'tm':'Trimmed_Mean'} 
        units = unit_dict[given_unit] 

        Eggnog_sample.option_unit = units
        
        # if the parsed unit is TPM, we will use RPKM for calculations and then transform it to TPM
        if given_unit == 'tpm': 
            Eggnog_sample.calc_unit = 'RPKM'
        else:
            Eggnog_sample.calc_unit = units
    
    @classmethod
    def init_sample_list(cls, sample_list):
        Eggnog_sample.sample_list = sample_list


    def define_samplename(self):

        """
        Instance method to extract samplename from the filename
        """

        basename = os.path.basename(self.filename)
        self.samplename = re.sub(r'.emapper.*', '', basename) # filename needs to be of format: sample.emmapper.annotations
        
        return self.samplename
    
    def load_sample(self, orf_dict, og_dict):

        """
        Instance method to load all rows from a file as eggnog_orf instances and store them as a 
        eggnog_sample instance
        """
        
        with open(self.filename,"r") as file:
            for line in file:
                if not line.startswith("##"): # skip headers

                    if line.startswith("#"):
                        self.header = line.strip() #.split('\t') # column names as string, eliminar #??
                    else:  # read lines
                        items = line.strip().split('\t')
                        eggnog_ogs = items[4]
                        raw_ko = items[11]
                        
                        
                        if self.remove_euk and '@2759' in eggnog_ogs: # remove euk. Esto puede ser un argumento 
                            continue
                        
                        elif '@10239' in eggnog_ogs: # if virus
                            continue

                        else:
                            query = items[0]
                            description = items[7]
                            # preferred_name = items[8]
                            # kegg_pathway = items[12]
                            # contig = re.sub(r'_[0-9]*$', '', query)
                            abundance = orf_dict[query]['abundance']
    
                            try:
                                og, kingdom = find_basal(eggnog_ogs)
                                og_dict = self.add_og_abundance(og, abundance, description, kingdom, og_dict)
                                self.mapped_og += float(abundance)
                            except:
                                # if that didn't work is because the og belongs to a virus. We don't take into account. 
                                #print(eggnog_ogs)
                                og = '@'
                                kingdom = 'Virus'

                            if raw_ko != '-':
                                kegg_ko = get_ko_list(items[11])
                                self.add_ko_abundance(kegg_ko, abundance)
                                # self.mapped_ko += float(abundance) 
                                self.mapped_ko += (float(abundance)*len(kegg_ko)) # adding up kos
                            else:
                                kegg_ko = '-'

                            #self.total += float(abundance) # para añadirlo al total y poder calcular bien la abundancia relativa no?

                            # es posible que esto no me haga falta
                            # eggnog_orf = Eggnog_orf(query, og, kingdom, description, preferred_name, kegg_ko, kegg_pathway, abundance)
                            # self.rows.append(eggnog_orf)

                            
                            # if we want to add up abundance for each ko :
                            # self.mapped_ko += abundance * len(kegg_ko)
                            # self.total_ko += abundance * len(kegg_ko)

                            # # self.query_list.append(query)
                            # # self.query_dict[query] = kegg_ko
                            # # self.all_dict[query] = {}
                            # # self.all_dict[query]['ko'] = kegg_ko
                            # # self.all_dict[query]['cog'] = find_basal(eggnog_ogs)
                            # # self.all_dict[query]['description'] = description
        return og_dict
    

    
    def add_og_abundance(self, og, abundance, des, king, og_dict):
    #def update_og_abundance(self, og, abundance, des, king, og_dict):

        """
        calculate the total abundance for each og in a sample
        """

        # if the og is not in the dictionary, initialize key to 0
        if og not in self.og_abundance.keys():
            self.og_abundance[og] = 0
            

        # add abundance:    
        self.og_abundance[og] += float(abundance)

        # if the og is not in the global og_dict initialize it in the dictionary
        if og not in og_dict.keys():
            og_dict[og] = {}
            og_dict[og]['description'] = des # save the og description 
            og_dict[og]['kingdom'] = king # save the og kingdom
            for sample in Eggnog_sample.sample_list:
                og_dict[og][sample] = 0
            
    
        return og_dict #, self.og_abundance
    
    def add_ko_abundance(self, kos, abundance):
        
        """
        add abundance to each ko on the list
        """
        # divide abundance by number of kos annotated in the contig
        #abun = float(abundance)/len(kos)
        abun = float(abundance) # adding up kos

        for ko_id in kos:
            # initialize dictionary for each ko
            if not ko_id in self.ko_abundance.keys():
                self.ko_abundance[ko_id] = 0
            
            # add ko abundance
            self.ko_abundance[ko_id] += abun # dividing by ko number
            # adding up
            # ko_abundance_sample[ko_id] += float(abundance) 
    
        #return self.ko_abundance

    def calculate_og_abundance(self, og_dict:dict):
       
        if Eggnog_sample.option_unit == 'TPM':

            for og in self.og_abundance.keys():
                    
                og_dict[og][self.samplename] = (self.og_abundance[og]/self.total)*10**6
                #og_dict[og][self.samplename] = (self.og_abundance[og]/self.mapped_og)*10**6 # relative to mapped
                
            og_dict = check_unmapped(og_dict, Eggnog_sample.sample_list)
            #tpm_mapped_og = (self.mapped_og/self.total)*10**6 # MAPPED IN TPM
            #og_dict['UNMAPPED'][self.samplename] = 1000000 * (self.total - self.mapped_og)/self.total # es lo mismo
            og_dict['UNMAPPED'][self.samplename] = 1000000 - (self.mapped_og/self.total)*10**6
            og_dict['UNMAPPED']['kingdom'] = '@'

        else: 

            for og in self.og_abundance.keys():
                    
                og_dict[og][self.samplename] = self.og_abundance[og]/self.total
                #og_dict[og][self.samplename] = (self.og_abundance[og]/self.mapped_og) # relative to mapped
            
            og_dict = check_unmapped(og_dict, Eggnog_sample.sample_list)
            
            og_dict['UNMAPPED'][self.samplename] = 1 - self.mapped_og/self.total
            og_dict['UNMAPPED']['kingdom'] = '@'
        
    
            # except:
            #     og_dict[og] = {}
            #     og_dict[og]['kingdom'] = og_dict[og]  
            #     og_dict[og]['description'] = og_description[og]
            #     for sample_id in sample_list:
            #         rel_og_abun[og][sample_id] = 0

            #rel_og_abun[og][samplename] = og_abundance_sample[og]/total_og_abun*10**6     

        return og_dict
    
    def calculate_ko_abundance(self, ko_dict, kos_legend):

        """
        Calculate every ko total abundance in a sample. 
        This function relies on contigs and orf being sorted.
        Takes rpkm value as abundance
        """
        # CHECK WHEN A SEED CORRESPOND TO SEVERAL KOS
        # more_kos = []
        # total_kos = 0 
        
        if Eggnog_sample.option_unit == 'TPM':

            for ko_id in self.ko_abundance.keys():

                self.global_ko_list.append(ko_id)

                if not ko_id in ko_dict.keys():
                    ko_dict[ko_id] = {}
                    try: 
                        ko_dict[ko_id]['description'] = kos_legend[ko_id]['description']
                    except:
                        ko_dict[ko_id]['description'] = '@'
                    
                    for sample_id in Eggnog_sample.sample_list:
                        ko_dict[ko_id][sample_id]=0
            
                ko_dict[ko_id][self.samplename] = (self.ko_abundance[ko_id]/self.total)*10**6
                #ko_dict[ko_id][self.samplename] = self.ko_abundance[ko_id]/self.mapped_ko*10**6 # relative to mapped

            ko_dict = check_unmapped(ko_dict, Eggnog_sample.sample_list)
            
            ko_dict['UNMAPPED'][self.samplename] = 1000000 - (self.mapped_ko/self.total)*10**6 

        else:

            for ko_id in self.ko_abundance.keys():

                self.global_ko_list.append(ko_id)

                if not ko_id in ko_dict.keys():
                    ko_dict[ko_id] = {}
                    try: 
                        ko_dict[ko_id]['description'] = kos_legend[ko_id]['description']
                    except:
                        ko_dict[ko_id]['description'] = '@'
                    
                    for sample_id in Eggnog_sample.sample_list:
                        ko_dict[ko_id][sample_id]=0
            
                ko_dict[ko_id][self.samplename] = self.ko_abundance[ko_id]/self.total
                #ko_dict[ko_id][self.samplename] = self.ko_abundance[ko_id]/self.mapped_ko # relative to mapped
            
            ko_dict = check_unmapped(ko_dict, Eggnog_sample.sample_list)
            ko_dict['UNMAPPED'][self.samplename] = 1 - self.mapped_ko/self.total


        # CHECK WHEN A SEED CORRESPOND TO SEVERAL KOS
        # total = len(more_kos)
        # two = more_kos.count(2)
        # three = more_kos.count(3)
        # rest = total - two - three 
        # print(total_kos, round((total/total_kos)*100,2), total, two, three, rest)


        return ko_dict
            

    def calculate_KEGG_pathway_completeness(self, path_coverage, KEGG_dict):

        """
        Function to calculate KEGG pathway completeness of each sample 
        """

        kegg_cov_dict = {}

        for kegg_p, annotation in KEGG_dict.items():
            kegg_id = str('ko'+kegg_p)
            pathway_description = annotation[0]
            kegg_number = annotation[1]
            kegg_cov_dict[kegg_id] = 0   
            for ko in annotation[2]:
                ko_id = ko['KO']
                if ko_id in self.global_ko_list:
                    kegg_cov_dict[kegg_id] +=1
            
            if kegg_cov_dict[kegg_id] != 0:
                coverage = kegg_cov_dict[kegg_id]/kegg_number
                if coverage > 0.1: # cut-off proporcion
                    if not kegg_id in path_coverage.keys():
                        path_coverage[kegg_id] = {}
                        path_coverage[kegg_id]['description'] = pathway_description
                        for sample_id in Eggnog_sample.sample_list:
                            path_coverage[kegg_id][sample_id] = 0
                    
                    path_coverage[kegg_id][self.samplename] = coverage
                    
        return path_coverage


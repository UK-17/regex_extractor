from os import error
import re #regex library
import json #JSON library
from pathlib import Path #to load the files
import logging #logger
import logging.config
import textract
from textract.parsers import process#custom class to extract text from docx file
from core.medicine_scraper import MedicineScraper
import sys
sys.path.insert(0,'..')
from utils.utils import FileOperations,ErrorHandler


""" Importing logger at the top level. """

logging.config.fileConfig('logging.conf')
logger = logging.getLogger(__name__)


class MedicalExtractor:

    """ Extracts demographic/medicine data from a medical document. """

    REGEX_FILE_PATH = str(FileOperations.get_project_root())+"/data/regex_mapping.json" #regex file path
    FIELDS_TO_EXTRACT = ['PATIENT_NAME','AGE','GENDER','MRN','DATE_OF_DISCHARGE','DOB','DIAGNOSIS'] #demographics field that we extract
    DOCUMENT_SECTIONS = [('MEDICINE_SECTION',2),('DEMOGRAPHICS_SECTION',2),('EMERGENCY_SECTION',0)] #important sections of the document and threshold value for keywords to catch.

    def __init__(self,**kwargs) -> None:

        """ Initializing the Extractor by passing document. """

        self.file_path = None #file path of the document passed
        self.text = self.__docx_to_str(kwargs) #text extracted from file/input stringsss
        self.regex_mapper = self.__load_regex() #load the regex from file
        self.sections = self.__break_in_sections() #divide the text nto sections
        self.demographics_data = self.__extract_fields(MedicalExtractor.FIELDS_TO_EXTRACT) #extract demographics data
        self.emergency_data = self.__extract_emergency_data() #extract emergency data
        self.medicines = self.__extract_medicines_regex() #extract medicines data
        self.output = self.__return_extracted_data() #final output 
        
    def __load_regex(self) -> dict:

        """ Loading the regex mapper file as a dictionary. """

        regex_file = Path(MedicalExtractor.REGEX_FILE_PATH) #define the regex file
        with open(regex_file, "r") as read_file: #open the regex file
            mapper = json.load(read_file) #load the regex file as a dictionary
        return mapper #return regex mapper

    
    def __docx_to_str(self,params:dict) -> str:

        """ Extract data from the document and convert it to a string. """

        if 'input_str' in params.keys() and params['input_str'] is not None: #need to parse string
            result = params['input_str']
        elif 'input_file' in params.keys() and params['input_file'] is not None: #need to parse a docx file
            file_path = params['input_file'] #filepath to the file
            result  = textract.process(file_path) #extract text from document

        if type(result)==bytes:
            result = str(result,'utf-8')    
        
        return result #return extracted text
    
    def __break_in_sections(self) -> list:

        """ Break the text into sections depending on the delimiter. """

        delimiter = self.regex_mapper['DELIMITERS']['SECTION'] #delimiter on which the text will be broken into sections
        whole_text = self.text #load text to temp variable
        sections = re.split(delimiter,whole_text) #splitting the text on the delimiter
        result = list()
        for para in sections:
            start = whole_text.find(para)
            end = start + len(para)
            tag = self.__tag_sections(para)
            result.append({'tag':tag,'text':para,'span':(start,end)}) #indexing of the section
        
        
        
        logger.info(f'Tokenised Text : {result}')
        return result #return a list of sections
    
    def __tag_sections(self,para:str) -> str:

        """ Tags sections based on certain keywords. """

        sections = MedicalExtractor.DOCUMENT_SECTIONS
        for section,threshold in sections:
            tag = 'UNCATEGORIZED'
            pattern = self.__make_regex_pattern(nested=False,keyword=section)
            if len(re.findall(pattern,para))>threshold: 
                tag = section
                break
        return tag

        

    
    def __make_regex_pattern(self,nested:bool,keyword:str)->str:

        """ Return a regex pattern for a given key from the regex mapper dictionary. """

        search_dict = self.regex_mapper[keyword] #load the relevant regex dictionary
        if nested: #if the pattern is nested
            searchkey = search_dict['SEARCH_KEY']
            delimiter = search_dict['SEARCH_DELIMITER']
            pattern = search_dict['SEARCH_PATTERN']
            raw_string = r"{}{}{}".format(searchkey,delimiter,pattern)
        else:
            pattern = search_dict
            raw_string = r"{}".format(pattern)
        if nested:
            logger.info(f'keyword:{keyword}|pattern:{raw_string}')
        regex_str = re.compile(raw_string,re.IGNORECASE|re.DOTALL|re.MULTILINE) #add flags and make a regex pattern
        return regex_str
    
    def __get_params(self,key_to_search,is_nested=True) -> str:

        """ Extract the required field from the text. """

        try:
            searchstr = self.__make_regex_pattern(nested=is_nested,keyword=key_to_search) #fetch the regex pattern
        except Exception as e:
            error = ErrorHandler(e,f"{key_to_search} not defined in regex_mapping.json")
            error.log_error()
            return "N/A"

        try:
            retval = [each.groupdict() for each in re.finditer(searchstr,self.text)]
            logger.info('Regex caught {}:{}'.format(key_to_search,retval))
            retval = retval[0]
            retval = retval[key_to_search] #caught data for the key
        except Exception as e:
            error = ErrorHandler(e,f'{key_to_search} not found')
            error.log_error()
            retval='N/A'
        
        logger.info("Param Returned:{} Value is :{}".format(key_to_search,retval))
        return retval #returning value for the key
    

    def __extract_fields(self,fields_to_extract:list) -> dict:

        """ Driver function to extract all the fields. """

        result = dict()
        for keyword in fields_to_extract:
            extracted_information = self.__get_params(keyword) #extract data for a key
            logger.info(f'{keyword}:{extracted_information}')
            result[keyword]=extracted_information #add fielfname,caught data to collection
        
        logger.info(f'Extracted data : {result}')
        return result #return all caught demographics data
    
    def __scrape_medicine(self,medicine:dict) -> dict:

        """ Getting brand name,generic name mapping for a medicine. """

        name = medicine['NAME']
        med_scraper = MedicineScraper(name) #scraping for a search string
        brand_name,generic_name,isExact = med_scraper.return_data() #getting metadata
        medicine['BRAND_NAME'] = brand_name
        medicine['GENERIC_NAME'] = generic_name
        del medicine['NAME']
        return medicine
    
    def __refine_medicines(self,medicines:list) -> list:

        """ Cleanup the medicines extracted. """

        result = list()
        for index,medicine in enumerate(medicines):
                medicine['COMMENTS'] = self.text[medicine['span'][1]:medicines[index+1]['span'][0]].strip() if index!=len(medicines)-1 else '' #adding uncategorized information as comments
                del medicine['span']
                if medicine['DOSAGE'] is None and medicine['FREQUENCY'] is not None: #making frequency and dosage into understandable format
                    temp = medicine['FREQUENCY'].split('-')
                    medicine['FREQUENCY'] = '-'.join(['1' if each!='0' else '0' for each in temp])
                    medicine['DOSAGE']=temp[0]
                
                medicine = { k:('N/A' if v is None else v.strip()) for k, v in medicine.items()} #uncaught data is returned as 'N/A'
                medicine = self.__scrape_medicine(medicine)
                result.append(medicine)
                    
        return result #return cleaned up medicines

    
    def __extract_medicines_regex(self) -> list:

        """ Extract Medicines by regex method. """

        medicines = list()
        medicine_pattern = self.__make_regex_pattern(keyword='MEDICINE',nested=False) #medicine regex pattern
        try:
            medicines_section = [each['text'] for each in self.sections if each['tag']=='MEDICINE_SECTION'][0]
        except Exception as e:
            error = ErrorHandler(e,'No Medical section found. Searching for medicines in the entire document.')
            error.log_error()
            medicines_section = self.text
        retval = re.finditer(medicine_pattern,medicines_section) #match objects for all caught medicines
        for match in retval: #structure medicine into list of dictionaries
            logger.info(match)
            span = match.span()
            medicine_data = match.groupdict()
            medicine_data['span']=span
            medicines.append(medicine_data)
        
        medicines = self.__refine_medicines(medicines) #cleanup up medicines
            
        logger.info(medicines)
        return medicines #returning medicines caught by regex
    
    def __extract_emergency_data(self) -> str:

        """ Collect emergency conditions/procedures mentioned in the document. """

        result = [each['text'] for each in self.sections if each['tag']=='EMERGENCY_SECTION']
        return '\n'.join(result)



    
    def __return_extracted_data(self) -> dict:

        """ Returning output data in a categorized manner. """

        return {'demographics':self.demographics_data,'emergency':self.emergency_data,'medicines':self.medicines}
    

            

if __name__=="__main__":
    file_path = "/home/vesper/Projects/regex_extractor/data/sample_files/angio.docx"
    ext_obj = MedicalExtractor(input_file=file_path)
    logger.info(f'OUTPUT : {ext_obj.output}')
    print(ext_obj.output)


        


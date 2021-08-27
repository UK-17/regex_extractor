import re
import json
from pathlib import Path
import logging
import logging.config
import docx
from docx.api import Document
from handle_docx import HandleDocx



logging.config.fileConfig('logging.conf')
logger = logging.getLogger(__name__)

class MedicalExtractor:

    FIELDS_TO_EXTRACT = ['PATIENT_NAME','AGE','GENDER','MRN','DATE_OF_DISCHARGE','DOB','DIAGNOSIS']

    def __init__(self,**kwargs) -> None:

        self.file_path = None
        self.text = self.__docx_to_str(kwargs)
        self.regex_file = Path("regex_mapping.json")
        self.regex_mapper = dict()
        with open(self.regex_file, "r") as read_file:
            self.regex_mapper = json.load(read_file)

        self.sections = self.__break_in_sections()
        self.extracted_data = self.__extract_fields(MedicalExtractor.FIELDS_TO_EXTRACT)
        self.medicines = self.__extract_medicines_regex()
        

    
    def __docx_to_str(self,params:dict) -> str:

        if 'input_str' in params.keys() and params['input_str'] is not None:
            result = params['input_str']
        elif 'input_file' in params.keys() and params['input_file'] is not None:
            self.file_path = params['input_file']
            result  = HandleDocx(docx.Document(params['input_file'])).load_data()
        
        return result

    
    def __make_regex_pattern(self,nested:bool,keyword:str)->str:
        search_dict = self.regex_mapper[keyword]
        if nested:
            searchkey = search_dict['SEARCH_KEY']
            delimiter = search_dict['SEARCH_DELIMITER']
            pattern = search_dict['SEARCH_PATTERN']
            raw_string = r"{}{}{}".format(searchkey,delimiter,pattern)
        else:
            pattern = search_dict
            raw_string = r"{}".format(pattern)
        logger.info(f'keyword:{keyword}|pattern:{raw_string}')
        regex_str = re.compile(raw_string,re.IGNORECASE|re.DOTALL|re.MULTILINE)
        return regex_str
    
    def __get_params(self,key_to_search,is_nested=True):

        try:
            searchstr = self.__make_regex_pattern(nested=is_nested,keyword=key_to_search)
        except:
            logger.critical(f"{key_to_search} not defined in regex_mapping.json")
            return "N/A"

        try:
            retval = [each.groupdict() for each in re.finditer(searchstr,self.text)]
            logger.info('Regex caught {}:{}'.format(key_to_search,retval))
            retval = retval[0]
            retval = retval[key_to_search]
        except Exception as e:
            logger.error(e)
            logger.critical('{} not found'.format(key_to_search))
            retval='N/A'
        
        logger.info("Param Returned:{} Value is :{}".format(key_to_search,retval))
        return retval
    

    def __extract_fields(self,fields_to_extract:list):
        result = dict()
        for keyword in fields_to_extract:
            extracted_information = self.__get_params(keyword)
            logger.info(f'{keyword}:{extracted_information}')
            result[keyword]=extracted_information
        
        logger.info(f'Extracted data : {result}')
        return result
    
    def __refine_medicines(self,medicines:list):
        result = list()
        for index,medicine in enumerate(medicines):
                medicine['COMMENTS'] = self.text[medicine['span'][1]:medicines[index+1]['span'][0]].strip() if index!=len(medicines)-1 else ''
                del medicine['span']
                if medicine['DOSAGE'] is None and medicine['FREQUENCY'] is not None:
                    temp = medicine['FREQUENCY'].split('-')
                    medicine['FREQUENCY'] = '-'.join(['1' if each!='0' else '0' for each in temp])
                    medicine['DOSAGE']=temp[0]
                
                medicine = { k:('N/A' if v is None else v.strip()) for k, v in medicine.items()}
                result.append(medicine)
                    
        return result

    
    def __extract_medicines_regex(self):
        medicines = list()
        medicine_pattern = self.__make_regex_pattern(keyword='MEDICINE',nested=False)
        retval = re.finditer(medicine_pattern,self.text)
        for match in retval:
            logger.info(match)
            span = match.span()
            medicine_data = match.groupdict()
            medicine_data['span']=span
            medicines.append(medicine_data)
        
        medicines = self.__refine_medicines(medicines)
            
        logger.info(medicines)
        return medicines
    
    def __break_in_sections(self):
        delimiter = self.regex_mapper['DELIMITERS']['SECTION']
        whole_text = self.text
        sections = re.split(delimiter,whole_text)
        result = list()
        for para in sections:
            start = whole_text.find(para)
            end = start + len(para)
            result.append({'text':para,'span':(start,end)})
        
        logger.info(f'Tokenised Text : {result}')
        return result
            






if __name__=="__main__":
    file_path = "sample_files/JSS-2.docx"
    ext_obj = MedicalExtractor(input_file=file_path)


        


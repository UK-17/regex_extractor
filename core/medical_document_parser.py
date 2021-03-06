import os
import re
import json
from pathlib import Path
import logging
import logging.config
from core.text_extractor import TextExtractor
from core.medicine_scraper import MedicineScraper
import sys
from fastapi import HTTPException

sys.path.insert(0, '..')
from utils.utils import FileOperations, ErrorHandler

""" Importing logger at the top level. """

logging.config.fileConfig('logging.conf')
logger = logging.getLogger(__name__)


class MedicalExtractor:
    """ Extracts demographic/medicine data from a medical document. """

    NO_OF_DAYS_TO_MONITOR = 7  # default monitoring duration
    REGEX_FILE_PATH = str(FileOperations.get_project_root()) + "/data/regex_mapping.json"  # regex file path
    FREQUENCY_MAPPING = str(
        FileOperations.get_project_root()) + "/data/frequency_mapping.json"  # frequency mapping file path
    FIELDS_TO_EXTRACT = ['PATIENT_NAME', 'AGE', 'GENDER', 'MRN', 'DATE_OF_DISCHARGE', 'DOB',
                         'DIAGNOSIS']  # demographics field that we extract
    DOCUMENT_SECTIONS = [('MEDICINE_SECTION', 2), ('DEMOGRAPHICS_SECTION', 2), (
        'EMERGENCY_SECTION', 0)]  # important sections of the document and threshold value for keywords to catch.

    def __init__(self, **kwargs) -> None:

        """ Initializing the Extractor by passing document. """

        self.file_path = None  # file path of the document passed

        try:
            self.text = self.__extract_text(kwargs)  # text extracted from file
            logger.info(f'EXTRACTED TEXT : {self.text}')
        except Exception as e:
            msg = 'Error while extracting text from the document'
            logger.error(e)
            logger.critical(msg)
            raise HTTPException(status_code=500, detail=msg)

        try:
            self.regex_mapper = self.__load_regex()  # load the regex from file
        except Exception as e:
            msg = 'Regex mapping file is missing.'
            logger.error(e)
            logger.critical(msg)
            raise HTTPException(status_code=501, detail=msg)

        try:
            self.sections = self.__break_in_sections()  # divide the text into sections
        except Exception as e:
            msg = 'Could not break the text into sections.'
            logger.error(e)
            logger.critical(msg)

        try:
            self.demographics_data = self.__extract_fields(
                MedicalExtractor.FIELDS_TO_EXTRACT)  # extract demographics data
        except Exception as e:
            msg = 'Error while extracting demographics data.'
            logger.error(e)
            logger.critical(msg)
            self.demographics_data = None

        try:
            self.emergency_data = self.__extract_emergency_data()  # extract emergency data
        except Exception as e:
            msg = 'Error while extracting emergency data.'
            logger.error(e)
            logger.critical(msg)
            self.emergency_data = None

        try:
            self.medicines = self.__extract_medicines_regex()  # extract medicines data
        except Exception as e:
            msg = 'Error while extracting medicines.'
            logger.error(e)
            logger.critical(msg)
            self.medicines = None

        try:
            self.output = self.__return_extracted_data()  # final output
        except Exception as e:
            msg = 'Error while generating output.'
            logger.error(e)
            logger.critical(msg)
            self.output = None

    @staticmethod
    def __load_regex() -> dict:

        """ Loading the regex mapper file as a dictionary. """

        regex_file = Path(MedicalExtractor.REGEX_FILE_PATH)  # define the regex file
        with open(regex_file, "r") as read_file:  # open the regex file
            mapper = json.load(read_file)  # load the regex file as a dictionary
        return mapper  # return regex mapper

    @staticmethod
    def __extract_text(params: dict) -> str:

        """ Extract data from the document and convert it to a string. """

        file_path = params['input_file']  # filepath to the file
        method = 'PDF_T' if '.pdf' in file_path else 'DEFAULT'
        processed_text = TextExtractor(file_path=file_path, method=method)
        result = processed_text.extracted_text
        return result  # return extracted text

    def __break_in_sections(self) -> list:

        """ Break the text into sections depending on the delimiter. """

        delimiter = self.regex_mapper['DELIMITERS'][
            'SECTION']  # delimiter on which the text will be broken into sections
        whole_text = self.text  # load text to temp variable
        sections = re.split(delimiter, whole_text)  # splitting the text on the delimiter
        result = list()
        for para in sections:
            start = whole_text.find(para)
            end = start + len(para)
            tag = self.__tag_sections(para)
            result.append({'tag': tag, 'text': para, 'span': (start, end)})  # indexing of the section

        logger.info(f'Tokenized Text : {result}')
        return result  # return a list of sections

    def __tag_sections(self, para: str) -> str:

        """ Tags sections based on certain keywords. """

        sections = MedicalExtractor.DOCUMENT_SECTIONS
        for section, threshold in sections:
            tag = 'UNCATEGORIZED'
            pattern = self.__make_regex_pattern(nested=False, keyword=section)
            if len(re.findall(pattern, para)) > threshold:
                tag = section
                break
        return tag

    def __make_regex_pattern(self, nested: bool, keyword: str) -> str:

        """ Return a regex pattern for a given key from the regex mapper dictionary. """

        search_dict = self.regex_mapper[keyword]  # load the relevant regex dictionary
        if nested:  # if the pattern is nested
            searchkey = search_dict['SEARCH_KEY']
            delimiter = search_dict['SEARCH_DELIMITER']
            pattern = search_dict['SEARCH_PATTERN']
            raw_string = r"{}{}{}".format(searchkey, delimiter, pattern)
        else:
            pattern = search_dict
            raw_string = r"{}".format(pattern)
        if nested:
            logger.info(f'keyword:{keyword}|pattern:{raw_string}')
        regex_str = re.compile(raw_string,
                               re.IGNORECASE | re.DOTALL | re.MULTILINE)  # add flags and make a regex pattern
        return regex_str

    def __get_params(self, key_to_search, is_nested=True) -> str:

        """ Extract the required field from the text. """

        try:
            searchstr = self.__make_regex_pattern(nested=is_nested, keyword=key_to_search)  # fetch the regex pattern
        except Exception as e:
            error = ErrorHandler(e, f"{key_to_search} not defined in regex_mapping.json")
            error.log_error()
            return "N/A"

        try:
            retval = [each.groupdict() for each in re.finditer(searchstr, self.text)]
            logger.info('Regex caught {}:{}'.format(key_to_search, retval))
            retval = retval[0]
            retval = retval[key_to_search]  # caught data for the key
        except Exception as e:
            error = ErrorHandler(e, f'{key_to_search} not found')
            error.log_error()
            retval = 'N/A'

        logger.info("Param Returned:{} Value is :{}".format(key_to_search, retval))
        return retval  # returning value for the key

    def __extract_fields(self, fields_to_extract: list) -> dict:

        """ Driver function to extract all the fields. """

        result = dict()
        for keyword in fields_to_extract:
            extracted_information = self.__get_params(keyword)  # extract data for a key
            logger.info(f'{keyword}:{extracted_information}')
            result[keyword] = extracted_information  # add filename,caught data to collection

        logger.info(f'Extracted data : {result}')
        return result  # return all caught demographics data

    @staticmethod
    def __scrape_medicine(medicine: dict) -> dict:

        """ Getting brand name,generic name mapping for a medicine. """

        name = medicine['NAME']
        med_scraper = MedicineScraper(name)  # scraping for a search string
        brand_name, generic_name, isExact = med_scraper.return_data()  # getting metadata
        medicine['BRAND_NAME'] = brand_name
        medicine['GENERIC_NAME'] = generic_name
        del medicine['NAME']
        return medicine

    def __refine_medicines(self, medicines: list) -> list:

        """ Cleanup the medicines extracted. """

        result = list()
        for index, medicine in enumerate(medicines):
            medicine['COMMENTS'] = self.medicines_section[
                                   medicine['span'][1]:medicines[index + 1]['span'][0] - 1].strip() if index != len(
                medicines) - 1 else ''  # adding uncategorized information as comments
            del medicine['span']
            if medicine['DOSAGE'] is None and medicine[
                'FREQUENCY'] is not None:  # making frequency and dosage into understandable format
                temp = medicine['FREQUENCY'].split('-')
                medicine['FREQUENCY'] = '-'.join(['1' if each != '0' else '0' for each in temp])
                medicine['DOSAGE'] = temp[0]

            medicine = {k: ('N/A' if v is None else v.strip()) for k, v in
                        medicine.items()}  # uncaught data is returned as 'N/A'
            medicine = self.__scrape_medicine(medicine)
            medicine = self.__correct_medicine_metadata(medicine)
            result.append(medicine)

        return result  # return cleaned up medicines

    @staticmethod
    def __correct_medicine_frequency(medicine: dict):

        """ Try to interpret frequency of the medicine. """

        # correcting frequency term.
        comments = medicine['COMMENTS']
        frequency = medicine['FREQUENCY']
        regex_file = Path(MedicalExtractor.FREQUENCY_MAPPING)  # define the frequency file
        with open(regex_file, "r") as read_file:  # open the frequency file
            frequency_mapper = json.load(read_file)  # load the frequency file as a dictionary
            if frequency == 'N/A' and len(comments) > 0:
                for term, synonyms in frequency_mapper.items():
                    for each in synonyms:
                        if each.lower() in comments.lower():
                            frequency = term
                medicine['FREQUENCY'] = frequency

        return medicine

    @staticmethod
    def __correct_medicine_duration(medicine: dict):

        """ Try to interpret frequency of the medicine. """

        # correcting duration term.
        comments = medicine['COMMENTS']
        duration = medicine['DURATION']
        if duration == 'N/A' and len(comments) > 0:
            if 'continue' in comments.lower():
                duration = MedicalExtractor.NO_OF_DAYS_TO_MONITOR
                medicine['DURATION'] = duration

        return medicine

    def __correct_medicine_metadata(self, medicine: dict):

        """ Categorize comments in one of the fields. """

        logger.info('Correcting medicine metadata.')

        medicine = self.__correct_medicine_frequency(medicine)  # correcting frequency for the medicine
        medicine = self.__correct_medicine_duration(medicine)  # correcting duration for the medicine

        return medicine

    def __extract_medicines_regex(self) -> list:

        """ Extract Medicines by regex method. """

        medicines = list()
        medicine_pattern = self.__make_regex_pattern(keyword='MEDICINE', nested=False)  # medicine regex pattern
        try:
            self.medicines_section = [each['text'] for each in self.sections if each['tag'] == 'MEDICINE_SECTION'][0]
        except Exception as e:
            error = ErrorHandler(e, 'No Medical section found. Searching for medicines in the entire document.')
            error.log_error()
            self.medicines_section = self.text
        retval = re.finditer(medicine_pattern, self.medicines_section)  # match objects for all caught medicines
        for match in retval:  # structure medicine into list of dictionaries
            logger.info(match)
            span = match.span()
            medicine_data = match.groupdict()
            medicine_data['span'] = span
            medicines.append(medicine_data)

        medicines = self.__refine_medicines(medicines)  # cleanup up medicines

        logger.info(medicines)
        return medicines  # returning medicines caught by regex

    def __extract_emergency_data(self) -> str:

        """ Collect emergency conditions/procedures mentioned in the document. """

        result = [each['text'] for each in self.sections if each['tag'] == 'EMERGENCY_SECTION']
        return '\n'.join(result)

    def __return_extracted_data(self) -> dict:

        """ Returning output data in a categorized manner. """

        return {'demographics': self.demographics_data, 'emergency': self.emergency_data, 'medicines': self.medicines}


if __name__ == "__main__":
    print(os.curdir())
    file_path = "/home/vesper/Projects/regex_extractor/data/sample_files/angio.docx"
    ext_obj = MedicalExtractor(input_file=file_path)
    logger.info(f'OUTPUT : {ext_obj.output}')
    print(ext_obj.output)

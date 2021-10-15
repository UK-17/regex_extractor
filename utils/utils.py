import os
import logging
logger = logging.getLogger(__name__)
import random
import string
from pathlib import Path




class ErrorHandler: #custom error handler

    def __init__(self,e:Exception,message:str) -> None:
        self.error = e
        self.message = message
    
    def log_error(self):
        logger.error(self.error)
        logger.critical(self.message)



        


class FileOperations: #various file operations done while parsing the document

    def is_file_supported(filename:str):

        SUPPORTED_FILE_TYPES = ['.docx','.pdf']

        """ check whether given file is supported """

        file_type = os.path.splitext(filename)[1]
        logger.info("File Extension : {}".format(file_type))
        if file_type in SUPPORTED_FILE_TYPES:
            return True
        else:
            return False


    def create_temp_file(filepath:str,file):

        """ create a replica to work on for the uploaded file """

        file_data = file.file.read()
        with open(filepath,'wb') as temp_file:
            temp_file.write(file_data)
        return filepath
    
    def get_project_root() -> Path:
        return Path(__file__).parent.parent

if __name__=="__main__":
    root = FileOperations.get_project_root()
    print(root)

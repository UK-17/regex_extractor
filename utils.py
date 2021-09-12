import os
import logging
logger = logging.getLogger(__name__)


def is_docx(filename:str):

    """ check whether given file is docx """

    file_type = os.path.splitext(filename)[1]
    logger.info("File Extension : {}".format(file_type))
    if file_type=='.docx':
        return True
    else:
        return False


def create_temp_file(filepath:str,file):

    """ create a replica to work on for the uploaded file """

    file_data = file.file.read()
    with open(filepath,'wb') as temp_file:
        temp_file.write(file_data)
    return filepath
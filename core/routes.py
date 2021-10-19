import os
from core.medical_document_parser import MedicalExtractor
from fastapi import APIRouter
from fastapi import File,UploadFile
import json

from utils.utils import FileOperations,ErrorHandler
from fastapi import APIRouter, Request, HTTPException

import logging
logger = logging.getLogger(__name__)



router=APIRouter()

@router.post('/parse-medical-document')
def parse_medical_document(request:Request,file:  UploadFile = File(...)):

    try:

        filename = file.filename #extracting filename of uploaded file
        
        if not FileOperations.is_file_supported(filename=filename): #if the uploaded filetype is supported
            logger.critical(f'{filename} is not in valid format. Exiting !!')
            raise HTTPException(status_code=422,detail=f'{filename} is unsupported filetype.')
        
        try: #creating a temp replica of uploaded file
            temp_file = FileOperations.create_temp_file(filepath=os.path.join(FileOperations.get_project_root(),"data",f"{filename}"),file=file)
        except Exception as e:
            error=ErrorHandler(e,'Error in file read/write')
            error.log_error()
            raise HTTPException(status_code=422,detail=e)
            
        
        extract_obj = MedicalExtractor(input_file=temp_file)
        result = extract_obj.output
        logger.info(f'Final Output:\n{json.dumps(result,indent=3)}')
        logger.info(f'Parsing Done.')
        return result
    
    except Exception as e:

        logger.error(e)
        logger.critical(f'Unknown Error while processing.')
        raise HTTPException(status_code=500,detail=e)


    

    
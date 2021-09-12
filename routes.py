from medical_document_parser import MedicalExtractor
from fastapi import APIRouter
from fastapi import File,UploadFile
import os
from utils import is_docx,create_temp_file
from fastapi import APIRouter, Request, HTTPException

import logging
logger = logging.getLogger(__name__)



router=APIRouter()

@router.post('/parse-medical-document')
def parse_medical_document(request:Request,file:  UploadFile = File(...)):
    
    filename = file.filename #extracting filename of uploaded file
    
    if not is_docx(filename=filename): #if the uploaded file is not docx format
        logger.critical(f'{filename} is not a docx file. Exiting')
        raise HTTPException(status_code=422,detail=f'{filename} is unsupported filetype.')
    
    try: #creating a temp replica of uploaded file
        temp_file = create_temp_file(filepath='temp.docx',file=file)
    except Exception as e:
        logger.error(e)
        logger.critical(f'Could not perform read/write on {filename}.')
        raise HTTPException(status_code=422,detail=e)
        
    
    extract_obj = MedicalExtractor(input_file=temp_file)
    result = extract_obj.output
    return result
    

    
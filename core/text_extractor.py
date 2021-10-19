import textract
import pdfplumber

class TextExtractor:

    def __init__(self,file_path,method='DEFAULT') -> None:
        self.filepath = file_path
        if method=='DEFAULT':self.extracted_text = self.textract_default()

    def textract_default(self):
        result  = textract.process(self.filepath) #extract text from document
        if type(result)==bytes:result = str(result,'utf-8')    
        return result #return extracted text


    def textract_pdf(self,filename:str):
        text = textract.process(filename=file_path,method='tesseract')
        text = str(text,'utf-8')
        return text

    def pdfplumber_extraxt(self,filename:str):
        with pdfplumber.open(filename) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                print(text)
        
        return True


if __name__=="__main__":
    file_path = '/home/vesper/vengage/files/revengagecardiaccare/rajan.pdf'
    text = TextExtractor.pdfplumber_extraxt(file_path)
    print(text)

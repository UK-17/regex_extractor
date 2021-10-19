import textract
import pdfplumber

class PDFExtractor:


    def textract_pdf(filename:str):
        text = textract.process(filename=file_path,method='tesseract')
        text = str(text,'utf-8')
        return text

    def pdfplumber_extraxt(filename:str):
        with pdfplumber.open(filename) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                print(text)
        
        return True


if __name__=="__main__":
    file_path = '/home/vesper/vengage/files/revengagecardiaccare/rajan.pdf'
    text = PDFExtractor.pdfplumber_extraxt(file_path)
    print(text)

from pathlib import Path
import docx
from docx.document import Document
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import _Cell, Table
from docx.text.paragraph import Paragraph
import logging
logger = logging.getLogger(__name__)

class HandleDocx:
    def __init__(self,filedocx):
        self.fileobj = filedocx
    
    def load_data(self):
        logger.critical("docx data :{}".format(self.fileobj))
        doc = self.fileobj
        all_data=[]  
        for block in self.iter_block_items(doc):
            if isinstance(block,Paragraph):
                all_data.append(block.text)
            if isinstance(block, Table):
                for row in block.rows:
                    row_data = []
                    for cell in row.cells:
                        for paragraph in cell.paragraphs:
                            if(paragraph.text is not None or paragraph.text !=""):
                                row_data.append(paragraph.text)
                            row_text=" ".join(elem for elem in row_data)
                    logger.info("Table data as concatenated data:{}".format(row_text))
                    all_data.append(row_text)
        return_data = "\n".join(elem for elem in all_data)
        return return_data
    
    def iter_block_items(self,parent):
        """
        Yield each paragraph and table child within *parent*, in document order.
        Each returned value is an instance of either Table or Paragraph. *parent*
        would most commonly be a reference to a main Document object, but
        also works for a _Cell object, which itself can contain paragraphs and tables.
        """
    
        if isinstance(parent, Document):
            parent_elm = parent.element.body
        elif isinstance(parent, _Cell):
            parent_elm = parent._tc
        else:
            raise ValueError("something's not right")

        for child in parent_elm.iterchildren():
            if isinstance(child, CT_P):
                yield Paragraph(child, parent)
            elif isinstance(child, CT_Tbl):
                yield Table(child, parent)

if __name__=="__main__":
    
    doc = docx.Document('sample_files/angio.docx')
    data_received = HandleDocx(doc).load_data()
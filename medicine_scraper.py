import requests
from bs4 import BeautifulSoup
import logging
import logging.config

logging.config.fileConfig('logging.conf')
logger = logging.getLogger(__name__)
    
class MedicineScraper:

    def __init__(self,name):
        self.search_string = name
        self.brand_name,self.generic_name,self.isExact = self.__scraper_fine()
    
    def return_data(self):
        return self.brand_name,self.generic_name,self.isExact


    def __extraction_from_raw_search(self,content):
        brand_name,generic_name= 'N/A',''
        soup = BeautifulSoup(content, 'html5lib')
        text = str(soup)
        path = '/india/drug/info/'
        cursor = text.find(path)
        offset = len(path) + len(self.search_string)+len('?mtype=generic')
        text = text[cursor:cursor+offset].strip()
        if text.find('?mtype=generic') >0: #given name is generic
            generic_names = self.search_string
        else: #given name is brand
                text = soup.get_text()
                cursor = text.find('Generic Name')
                extract = text[cursor:cursor+300]
                extract = extract.split()
                extract = ' '.join(extract)
                try:
                    generic_name = extract.split(':')[1].strip()
                except:
                    generic_name = ''
                if self.search_string.upper() ==generic_name.upper():
                    generic_name = self.search_string
                else:
                    brand_name=self.search_string
        isExact = False
        return brand_name,generic_name,isExact

    def __extraction_from_scraper_fine(self,content):
        soup = BeautifulSoup(content, 'html5lib')
        dump = str(soup)
        extract = soup.find("meta",attrs={'name':'DESCRIPTION'})
        brand_name = 'N/A'
        generic_name = ''
        if extract:
            extract = extract['content']
            extract = extract.split(':')[0]
            if extract.find('(')<0:
                generic_name = extract.upper()
            else:
                extract = extract.split('(')
                brand_name = extract[0].capitalize()
                generic_name = (extract[1].lower())
                generic_name = generic_name[:-1] #to remove ) bracket
                if generic_name[-1]=='.': generic_name = generic_name[:-1] # to remove . at the end
            isExact = True                  
            return brand_name,generic_name,isExact
        else:
            logger.info(f'Fine scraper did not get any match for {self.search_string}')
            isExact = False
            return self.__raw_search()

    
    def __raw_search(self):
        logger.info(f'Raw Search : {self.search_string}')
        url = 'https://www.mims.com/india/drug/search?q=' + self.search_string
        try:
            page = requests.get(url,timeout=5)
        except Exception as e:
            logger.error(e)
            logger.critical(f'Timeout:5s|URL:{url}')
            return self.search_string,'',False
        brand_name,generic_name,isExact= self.__extraction_from_raw_search(page.content)
        return brand_name,generic_name,isExact

    def __scraper_fine(self): 
        logger.info(f'Fine scraping : {self.search_string}')
        url = 'https://www.mims.com/india/drug/info/' + self.search_string
        try:
            page = requests.get(url,timeout=5)
        except Exception as e:
            logger.error(e)
            logger.critical(f'Timeout:5s|URL:{url}')
            return self.search_string,'',False
        
        brand_name,generic_name,isExact = self.__extraction_from_scraper_fine(page.content)
        return brand_name,generic_name,isExact
        

if __name__=="__main__":
    name = input('Medicine Name:')
    med_scraper = MedicineScraper(name)
    brand_name,generic_name,isExact = med_scraper.return_data()
    print(f'Brand:{brand_name}|Generic:{generic_name}|isExact:{isExact}')
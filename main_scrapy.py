import subprocess 
import scrapy 
from typing import List 
from scrapy.shell import inspect_response
from scrapy.spiders import CrawlSpider
from scrapy.crawler import CrawlerProcess 
from scrapy import Request 
from scrapy.http.response.html import HtmlResponse
from parsel import Selector 
from playwright.sync_api import sync_playwright
from playwright._impl._errors import Error,TimeoutError

class InfosSpider(scrapy.Spider):
    name = 'extractor'  

    tab_clearing_list = (
        'chrome://new-tab-page/',
        'about:blank'
    )

    def __init__(self,first_name:str,executable:str):
        self.first_name = first_name 
        self.executable = executable 
        self.playwright = sync_playwright().start()
        self.start_chrome()
        self.browser = self.playwright.chromium.connect_over_cdp("http://127.0.0.1:9222")
        self.context = self.browser.contexts[0]
        self.page = self.context.new_page()

    def start_chrome(self):
        self.process = subprocess.Popen(
                    [
                        executable,
                        '--remote-debugging-port=9222'
                        # '--headless'
                    ]
                )
        
    def start_requests(self):
        yield Request(
            'https://www.wvborc.com/verify',
            callback=self.parse_search
        )

    def parse_search(self,response):
        self.search(response)
        results_count = self.get_search_count()
        check_value = ''
        successive_empty_table = 0
        for index in range(2377,results_count + 1):
            self.refresh(response) if index % 500 ==0 else None # refresh the browser after 500 scraped items to not get out of memory problem
            try :
                self.select_search_result(index,check_value)
            except Error as e:
                check_value = ''
                successive_empty_table += 1
                if successive_empty_table > 1:
                    try :
                        self.page.wait_for_selector('#MainContent_grdPrevLics td',timeout=3000)
                    except TimeoutError :
                        yield self.get_primary_item(index)
                        continue 
                    yield self.extract_person_item(index)
                    successive_empty_table=0
                    continue
                else :
                    yield self.get_primary_item(index)
                    continue 
            successive_empty_table = 0
            yield self.extract_person_item(index)
            check_value = self.page.evaluate(
                "document.querySelector('#MainContent_grdPrevLics td').textContent"
            )
        
            if self.page.query_selector_all('//table[@id="MainContent_grdDispAct"]//tr[position()>1 and descendant::table]') :
                breakpoint()

    def search(self,response):
        self.page.goto(response.url)
        self.close_empty_tab()
        self.page.fill('//input[@id="MainContent_txtFindFName"]','%')
        self.page.keyboard.press('Enter')
        self.page.wait_for_function('document.querySelectorAll("#MainContent_lbUsers option").length > 1')

    def click_next(self,index:int,person_item:dict,check_value:str):
        self.page.query_selector_all('//a[contains(@href,"Page")]')[index].click()
        print(
            self.page.evaluate('document.querySelector("#MainContent_grdPrevLics td:nth-child(3)").textContent'),
            check_value
        )
        self.page.wait_for_function(
            f'document.querySelector("#MainContent_grdPrevLics td:nth-child(3)").textContent.trim() !== "{check_value}"'
        )

    def get_search_count(self):
        return len(
            self.page.query_selector_all(
                '//select[@id="MainContent_lbUsers"]/option'
            )
        ) - 1 

    def select_search_result(self,index:int,check_value:str):
        self.page.query_selector(
            '//select[@id="MainContent_lbUsers"]'
        ).select_option(index=index)
        self.page.wait_for_selector('#MainContent_grdPrevLics')
        self.page.wait_for_function(
            f"document.querySelector('#MainContent_grdPrevLics td').textContent !== '{check_value}'"
        )
    


    def get_license_rows(self,page_selector:Selector):
        return page_selector.xpath('//table[@id="MainContent_grdPrevLics"]/tbody/tr[position()>1 and not(descendant::table)]')

    def get_disciplinary_rows(self,page_selector:Selector):
        return page_selector.xpath('//table[@id="MainContent_grdDispAct"]//tr[position()>1]')

    def get_license_history_item(self,row:Selector) -> dict :
        item = {}
        item['License #'] = row.xpath('string(./td[1])').get().strip()
        item['Type'] = row.xpath('string(./td[2])').get().strip()
        item['Valid From'] = row.xpath('string(./td[3])').get().strip()
        item['Expiring'] = row.xpath('string(./td[4])').get().strip()
        item['Employer'] = row.xpath('string(./td[5])').get().strip()
        item['Status'] = row.xpath('string(./td[6])').get().strip()
        item['Attachements'] = row.xpath('string(./td[7])').get().strip()
        return item 
    
    def get_license_history_items_from_page(self,person_item:dict):
        license_rows = self.get_license_rows(Selector(text=self.page.content()))
        person_item['License History'] += [self.get_license_history_item(row) for row in license_rows]
    
    def get_all_history_license(self,person_item:dict):
        person_item['License History'] = []
        self.get_license_history_items_from_page(person_item)
        if self.page.query_selector(
            '//table[@id="MainContent_grdPrevLics"]'
            '/tbody/tr[position()>1 and descendant::table]'
        ):
            total_pages = len(self.page.query_selector_all('//a[contains(@href,"Page")]'))
            if total_pages > 10:
                breakpoint()
            # check_value = person_item['License History'][0]['Valid From'].strip()
            # for page_index in range(total_pages):
            #     self.click_next(page_index,person_item,check_value)
            #     self.get_license_history_items_from_page(person_item)
            #     check_value = person_item['License History'][(page_index+1)*5]['Valid From']

    def get_discipline_items(self,person_item:dict):
        discipline_rows = self.get_disciplinary_rows(Selector(text=self.page.content()))
        person_item['Disciplinary Actions'] = [self.get_disciplinary_item(row) for row in discipline_rows]


    def get_disciplinary_item(self,row:Selector) -> dict :
        item = {}
        item['Practitioner'] = row.xpath('string(.//td[1])').get().strip()
        item['Date From'] = row.xpath('string(.//td[2])').get().strip()
        item['Date To'] = row.xpath('string(.//td[3])').get().strip()
        item['Employer'] = row.xpath('string(.//td[4])').get().strip()
        item['Action Taken'] = row.xpath('string(.//td[5])').get().strip()
        item['State'] = row.xpath('string(.//td[6])').get().strip()
        item['Attachments'] = [
            f'https://www.wvborc.com/{url}' 
            for url in row.xpath('.//a/@href').getall()
        ]
        return item 

    def get_name(self,index):
        return self.page.query_selector(
            f'//select[@id="MainContent_lbUsers"]//option[{index}+1]'
        ).inner_text()

    def get_primary_item(self,index) -> dict:
        person_item = {}
        person_item['Name'] = self.get_name(index)
        person_item['Verification Document'] = f'https://www.wvborc.com/{self.page.query_selector('//a[@id="MainContent_btnReport"]').get_attribute('href')}'
        return person_item
    
    def extract_person_item(self,index):
        person_item = self.get_primary_item(index)
        print(index,person_item['Name'])
        self.get_all_history_license(person_item)
        self.get_discipline_items(person_item)
        return person_item  
    
    def refresh(self,response):
        self.logger.info('refreshing resources')
        self.process.terminate()
        self.page.close()
        self.context.close()
        self.browser.close()
        self.browser = self.playwright.chromium.connect_over_cdp("http://127.0.0.1:9222")
        self.context = self.browser.contexts[0]
        self.page = self.context.new_page()
        self.search(response)

    def close_empty_tab(self):
        for context in self.browser.contexts:
            for page in context.pages:
                if not page.url or page.url in self.tab_clearing_list:
                    page.close()

if __name__ == '__main__': 
    first_name = '%'
    executable = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
    process = CrawlerProcess(
        {
            'FEEDS' : {
                'output.json': {  
                    'format': 'json',  
                },
            },
            # 'HTTPCACHE_ENABLED' : True,
            # 'LOG_LEVEL':'ERROR'
        }
    )
    process.crawl(InfosSpider,first_name=first_name,executable=executable)
    process.start()
import subprocess
from playwright.sync_api import sync_playwright 
from playwright._impl._errors import Error 
from parsel import Selector 


executable = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"

process = subprocess.Popen(
            [
                executable,
                '--remote-debugging-port=9222'
                # '--headless'
            ]
        )


def get_search_count(page):
    return len(page.query_selector_all('//select[@id="MainContent_lbUsers"]/option')) - 1 

def select_search_result(page,index):
    page.query_selector('//select[@id="MainContent_lbUsers"]').select_option(index=index)

def get_page_selector(page):
    return Selector(text=page.content())

def get_license_rows(page_selector):
    return page_selector.xpath('//table[@id="MainContent_grdPrevLics"]/tbody/tr[position()>1 and not(descendant::table)]')

def get_disciplinary_rows(page_selector):
    return page_selector.xpath('//table[@id="MainContent_grdDispAct"]//tr[position()>1]')

def get_license_history_item(row) :
    item = {}
    item['License #'] = row.xpath('string(./td[1])').get()
    item['Type'] = row.xpath('string(./td[2])').get()
    item['Valid From'] = row.xpath('string(./td[3])').get()
    item['Expiring'] = row.xpath('string(./td[4])').get()
    item['Employer'] = row.xpath('string(./td[5])').get()
    item['Status'] = row.xpath('string(./td[6])').get()
    item['Attachements'] = row.xpath('string(./td[7])').get()
    return item 

def get_disciplinary_item(row):
    item = {}
    item['Practitioner'] = row.xpath('string(.//td[1])').get()
    item['Date From'] = row.xpath('string(.//td[2])').get()
    item['Date To'] = row.xpath('string(.//td[3])').get()
    item['Employer'] = row.xpath('string(.//td[4])').get()
    item['Action Taken'] = row.xpath('string(.//td[5])').get()
    item['State'] = row.xpath('string(.//td[6])').get()
    item['Attachments'] = row.xpath('string(.//td[7])').get()
    return item 

def get_name(page,index):
    return page.query_selector(
        f'//select[@id="MainContent_lbUsers"]//option[{index}+1]'
    ).inner_text()



playwright = sync_playwright().start()
browser = playwright.chromium.connect_over_cdp("http://127.0.0.1:9222")
context = browser.contexts[0]
page = context.new_page()

page.goto('https://www.wvborc.com/verify')
page.fill('//input[@id="MainContent_txtFindFName"]','%')
page.keyboard.press('Enter')
# page.query_selector('//select[@id="MainContent_lbUsers"]').select_option(index=2)
page.wait_for_timeout(5000)
results_count = get_search_count(page)
check_value = ''
for index in range(1616,results_count + 1):
    with page.expect_response('https://www.wvborc.com/verify') as response_info:
        select_search_result(page,index)
        print(index,get_name(page,index))
        page.wait_for_selector('//table[@id="MainContent_grdPrevLics"]')
        try :
            page.wait_for_function(f"document.querySelector('#MainContent_grdPrevLics td').textContent !== '{check_value}'")
            check_value = page.query_selector('#MainContent_grdPrevLics td').inner_text()
        except Error as e :
            print('error')
            page.wait_for_timeout(3000)
            continue

    if page.query_selector_all('//table[@id="MainContent_grdDispAct"]//tr[position()>1 and descendant::table]') :
        breakpoint()
breakpoint()

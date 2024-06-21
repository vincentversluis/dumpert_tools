# %% IMPORTS
import re
import time
from datetime import datetime
import arrow
from tqdm import tqdm

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException, TimeoutException, ElementClickInterceptedException                         

# %% CONSTANTS
PATH_COOKIES = "C:\\Users\\vince\\AppData\\Local\\Google\\Chrome\\User Data\\Default\\Network\\"
LINKS = {'dumpert':'https://www.dumpert.nl/',
         'dumpert_toppers_maand': 'https://www.dumpert.nl/toppers/maand',}
MONTHS_NL = ['januari', 'februari', 'maart', 'april', 'mei', 'juni', 'juli', 'augustus', 'september', 'oktober', 'november', 'december']
LAST_OF_MONTH = {'januari': 31,
                 'februari': 28,
                 'maart': 31,
                 'april': 30,
                 'mei': 31,
                 'juni': 30,
                 'juli': 31,
                 'augustus': 31,
                 'september': 30,
                 'oktober': 31,
                 'november': 30,
                 'december': 31}

# %% CONFIG
month_of_interest = 'mei' # Full Dutch month name
year_of_interest = '2024' # YYYY
bottom_n = 25

# %% FUNCTIONS
def get_prev_daymonthyear_of_interest(
        month_of_interest: str,
        year_of_interest: str
        ) -> str:
    """Return string version of previous month/year of interest"""
    month_of_interest = month_of_interest.lower()
    prev_month_of_interest = MONTHS_NL[MONTHS_NL.index(month_of_interest)-1]
    prev_year_of_interest = year_of_interest if month_of_interest != MONTHS_NL[-1] else year_of_interest-1
    return f"{LAST_OF_MONTH[prev_month_of_interest]} {prev_month_of_interest} '{prev_year_of_interest[-2:]}"

def clean_dumpert_datestring(datestring: str) -> str:
    """
    Clean dumpert datestring from something like:
        30 apr. '24 @ 22:04 | 40.634 views
     to
        30 apr '24    
    """
    return datestring.split('@')[0].replace('.', '').strip()

# %% MAIN
print(f"Opening a Browser")
chrome_options = webdriver.ChromeOptions() 
# Add regular cookies
chrome_options.add_argument(f"user-data-dir={PATH_COOKIES}")
driver = webdriver.Chrome(options=chrome_options)
address = LINKS['dumpert']
print(f"Going to {address}")
driver.get(address)
 
# Scroll until month before month of interest is opened
prev_dmy_of_interest = get_prev_daymonthyear_of_interest(
    month_of_interest, 
    year_of_interest)

print(f"Scrolling down page to videos dated {prev_dmy_of_interest}")
# Scroll down a good many times -- every month many videos are uploaded
# !! It helps having the browser window maximised
main_page = driver.find_element(By.TAG_NAME, 'html')
for _ in range(500):
    main_page.send_keys(Keys.PAGE_DOWN)

print("Scrolled a good way down, manually scroll further if necessary")

# %% Get videos and details
videos = {video_id: {'css': video}
          for video_id, video 
          in enumerate(driver.find_elements(By.CLASS_NAME, "css-6jb95j"))}

# Get video details
for video_id, video in tqdm(videos.items(), desc="Retrieving video details"):
    # Title
    title = video['css'].find_element(By.CLASS_NAME, "css-hp3yqo").text
    # url
    url = video['css'].get_attribute('href')
    # Date
    datestring = video['css'].find_element(By.CLASS_NAME, "css-13w4nb7").text
    datestring = clean_dumpert_datestring(datestring)
    if 'vandaag' in datestring:
        date = arrow.utcnow().to('CET').date()
    elif 'gister' in datestring:
        date = arrow.utcnow().to('CET').shift(days=-1).date()
    else:
        date = arrow.get(datestring, "D MMM 'YY", locale='nl-NL').date()
    # Score
    try:
        score = int(video['css'].find_element(By.CLASS_NAME, "css-1taeduy").text)
    except NoSuchElementException: # Negative score has a different class
        try:
            score = int(video['css'].find_element(By.CLASS_NAME, "css-1q6mey1").text)
        except NoSuchElementException: # Negative score has a different class
            score = None
    video.update({'date':       date,
                  'title':      title, 
                  'url':        url, 
                  'score':      score})
    
# Shut down browser
driver.close()

# %%
# Filter by date and acquire shit list
start_period_of_interest = arrow.get(
    f"1 {month_of_interest} {year_of_interest}"
    , "D MMM YYYY"
    , locale='nl-NL'
    ).date()
end_period_of_interest = arrow.get(
    f"{LAST_OF_MONTH[month_of_interest]} {month_of_interest} {year_of_interest}"
    , "D MMM YYYY"
    , locale='nl-NL'
    ).date()

# Filter videos for date
videos = {k: v for k, v in videos.items() if start_period_of_interest <= v['date'] <= end_period_of_interest}

# Sort videos by score
videos = dict(sorted(videos.items(), key=lambda x:x[1]['score']))

# Get shit list and show outcome
videos_shit = dict(list(videos.items())[:bottom_n])
for k, v in videos_shit.items():
    print(f"{v['score']:<5} - {v['title']}")

# %%
# Open shit list
print(f"Opening a Browser")
chrome_options = webdriver.ChromeOptions() 
# Add regular cookies
chrome_options.add_argument(f"user-data-dir={PATH_COOKIES}")
driver = webdriver.Chrome(options=chrome_options)

for k, v in videos_shit.items():
    driver.get(v['hyperlink'])
    driver.execute_script("window.open('');") 
    # Switch to the new window and open new URL 
    driver.switch_to.window(driver.window_handles[-1]) 
    # driver.get(v['url'])
# %%
driver.close()

# %%

# %% HEADER
# This script is written as an interactive notebook that requires VS Code with the
# Jupyter extension installed. The # %% delimiters are used to mark code cells, 
# mimicking the way Jupyter notebooks work.
#
# This script finds the worst rated videos in a given month on the Dutch video sharing 
# site dumpert.nl. On this site users can plus or minus videos. Usually ragebait
# videos are rated negatively, which is exactly what I intend to find. 
# 
# As the script relies on the browser to scroll down the page, it is best used to
# find the worst videos of the current or previous month. Very limited manual help
# might be required, though this is limited to manually scrolling down in a browser
# window, if the programmatic scrolling turns out to be too slow. Pay attention 
# to the comments within the script to signal these manual supports.

# %% IMPORTS
import arrow
from tqdm import tqdm

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException                         

# %% CONFIG
month_of_interest = 'maart'  # Full Dutch month name
year_of_interest = '2025'  # YYYY
bottom_n = 25  # Number of videos to output

# %% CONSTANTS
# Chrome cookies are usually stored in this folder:
PATH_COOKIES = "C:\\Users\\vince\\AppData\\Local\\Google\\Chrome\\User Data\\Default\\Network\\"
LINKS = {
    'dumpert':'https://www.dumpert.nl/',
    'dumpert_toppers_maand': 'https://www.dumpert.nl/toppers/maand',
    }
MONTHS_NL = ['januari', 'februari', 'maart', 'april', 'mei', 'juni', 'juli', 'augustus', 'september', 'oktober', 'november', 'december']
LAST_OF_MONTH = {  # Could not be bothered to faff with functions for this
    'januari': 31,
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
    'december': 31
    }

# %% FUNCTIONS
def get_prev_daymonthyear_of_interest(
        month_of_interest: str,
        year_of_interest: str
        ) -> str:
    """Return string version of previous month/year of interest, as used on dumpert.nl

    Args:
        month_of_interest (str): Target month
        year_of_interest (str): Target year

    Returns:
        str: Formatted string of month/year as used on dumpert.nl
    """
    month_of_interest = month_of_interest.lower()
    prev_month_of_interest = MONTHS_NL[MONTHS_NL.index(month_of_interest)-1]
    prev_year_of_interest = year_of_interest if month_of_interest != MONTHS_NL[-1] else str(int(year_of_interest)-1)
    return f"{LAST_OF_MONTH[prev_month_of_interest]} {prev_month_of_interest} '{prev_year_of_interest[-2:]}"

def clean_dumpert_datestring(datestring: str) -> str:
    """
    Clean dumpert datestring from something like:
        30 apr. '24 @ 22:04 | 40.634 views
    to
        30 apr '24    
        
    Args:
        datestring (str): Datestring as used on dumpert.nl

    Returns:
        str: Formatted string of month/year as recognisable by arrow
    """
    clean_datestring = (
        datestring
        .split('@')[0]
        .replace('.', '')
        .replace('maa', 'mrt')
        .strip()
        )
    return clean_datestring

# %% MAIN
# Open the browser and go to the dumpert.nl home page
# !! It helps having the browser window maximised
print("Opening a Browser")
chrome_options = webdriver.ChromeOptions() 
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
print("Manual interruption at that date is fine.")
# Scroll down a good many times -- every month many videos are uploaded
main_page = driver.find_element(By.TAG_NAME, 'html')
for _ in range(600):
    main_page.send_keys(Keys.PAGE_DOWN)

print("Scrolled a good way down, manually scroll further if necessary")
# %%
# !! Click 'open meer items' if the first day of the previous month is not reached 

# %% Get videos and details
videos = {
    video_id: {'css': video}
    for video_id, video 
    in enumerate(driver.find_elements(By.CLASS_NAME, "css-6jb95j"))
    }

# Get video details
for video_id, video in tqdm(videos.items(), desc="Retrieving video details"):
    title = video['css'].find_element(By.CLASS_NAME, "css-hp3yqo").text
    url = video['css'].get_attribute('href')
    datestring = video['css'].find_element(By.CLASS_NAME, "css-13w4nb7").text
    datestring = clean_dumpert_datestring(datestring)
    
    if 'vandaag' in datestring:
        date = arrow.utcnow().to('CET').date()
    elif 'gister' in datestring:
        date = arrow.utcnow().to('CET').shift(days=-1).date()
    else:
        date = arrow.get(datestring, "D MMM 'YY", locale='nl-NL').date()
        
    # Get score
    try:
        score = int(video['css'].find_element(By.CLASS_NAME, "css-1taeduy").text)
    except NoSuchElementException: # Negative score has a different class
        try:
            score = int(video['css'].find_element(By.CLASS_NAME, "css-1q6mey1").text)
        except NoSuchElementException: # Negative score has a different class
            score = None
    video.update({
        'date':       date,
        'title':      title, 
        'url':        url, 
        'score':      score
        })

print(f"Found {len(videos)} videos")

# Adjust year of interest if month is last month of year
adjusted_year_of_interest = year_of_interest if month_of_interest != MONTHS_NL[-1] else str(int(year_of_interest)-1)

# Filter by date and acquire shit list
start_period_of_interest = arrow.get(
    f"1 {month_of_interest} {adjusted_year_of_interest}"
    , "D MMMM YYYY"
    , locale='nl-NL'
    ).date()
end_period_of_interest = arrow.get(
    f"{LAST_OF_MONTH[month_of_interest]} {month_of_interest} {adjusted_year_of_interest}"
    , "D MMMM YYYY"
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
# Shut down browser when done collecting and sorting shit list. This is a separate
# step, as for debugging purposes, which are hopefully not needed, this saves having
# to open the browser and scroll all the way down again.
driver.close()

# %%
# Open each video of the shit list in a new tab
print("Opening a Browser")
chrome_options = webdriver.ChromeOptions() 
# Add regular cookies
chrome_options.add_argument(f"user-data-dir={PATH_COOKIES}")
driver = webdriver.Chrome(options=chrome_options)

for k, v in videos_shit.items():
    driver.get(v['url'])
    driver.execute_script("window.open('');") 
    # Switch to the new window and open new URL 
    driver.switch_to.window(driver.window_handles[-1]) 
    
# %%
# Close the browser, though user probably wants to do this themselves after enjoying
# the ragebait on the shit list
# driver.close()


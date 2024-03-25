from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from webdriver_manager.firefox import GeckoDriverManager
from selenium.common.exceptions import WebDriverException
import pandas as pd
import re
import urllib.parse
from body_finder import get_cleaned_html
from lead_extraction import extract_leads_from_html
import json
import time
import os

def get_phone(response_text):
    phone = re.search(r'\(?\b[2-9][0-9]{2}\)?[-. ]?[2-9][0-9]{2}[-. ]?[0-9]{4}\b', response_text)
    return phone.group(0) if phone else 'Phone number not found'

def get_email(response_text):
    email = re.search(r'([a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+\.[a-zA-Z0-9_-]+)', response_text)
    return email.group(0) if email else 'Email not found'

def extract_and_process_links(driver, base_url):
    driver.get(base_url)
    links = driver.find_elements("css selector", "a[href]")
    base_domain = urllib.parse.urlparse(base_url).netloc  # Extract the domain of the base URL
    results = []
    for link in links:
        href = link.get_attribute('href')
        link_domain = urllib.parse.urlparse(href).netloc  # Extract the domain of each found link
        # Check if the link domain is different from the base domain and not a LinkedIn URL
        if href and link_domain != base_domain and "linkedin.com" not in href and "twitter.com" not in href and "pinterest.com" not in href and "featured.com" not in href:
            results.append(href)
    return results


def setup_driver():
    options = Options()
    options.headless = True
    driver = webdriver.Firefox(service=Service(GeckoDriverManager().install()), options=options)
    return driver

def process_website(driver, url):
    try:
        driver.get(url)
        response_text = driver.page_source
        phone = get_phone(response_text)
        email = get_email(response_text)

        print(f'Processed {url}:') 
        print(f'Phone: {phone}, Email: {email}\n')
        return {'Website': url, 'Phone': phone, 'Email': email}
    except WebDriverException as e:
        print(f"Error accessing {url}: {e}")
        return None

# Setup Selenium WebDriver
driver = setup_driver()

# Load initial URLs from CSV
articles_df = pd.read_csv('mini-articles.csv')
# print("Loaded URLs:", articles_df['Website'].tolist())


with open('output.json', 'w') as f:
    url_to_leads_mapping = {}  # Initialize an empty dictionary
    for _, row in articles_df.iterrows():
        article_url = row['Website']
        result = get_cleaned_html(article_url)
        print(f"Processing webpage: {article_url}")
        print(f"Extracted HTML body content length: {len(result)}")
        print(f"Estimated token count: {round(len(result)/5)}")
        leads_json_str = extract_leads_from_html(result) # returns a json object of leads
        leads_python_obj = json.loads(leads_json_str)  
        print(f"JSON: {leads_json_str}")
        url_to_leads_mapping[article_url] = leads_python_obj                    
        f.seek(0)  # Move the file pointer to the beginning of the file
        json.dump(url_to_leads_mapping, f, indent=4)
        f.truncate()  # Truncate the file to the current position
        f.flush()  # Flush the buffer to ensure data is written to the file
        os.fsync(f.fileno())  # Force write of file to disk
        time.sleep(2)  # Wait for 2 second to prevent rate limiting issues
                                      
        # external_links = extract_and_process_links(driver, article_url)
        # print(f"Found {len(external_links)} external links from {article_url}")
        
        # for link in external_links:
        #     result = process_website(driver, link)
        #     if result:
        #         results.append(result)
        #         results_df = pd.DataFrame(results)
        #         results_df.to_csv('output_partial2.csv', index=False)

driver.quit()


print(json.dumps(url_to_leads_mapping, indent=4))

# Save results
# results_df = pd.DataFrame(results)
# results_df.to_csv('output.csv', index=False)

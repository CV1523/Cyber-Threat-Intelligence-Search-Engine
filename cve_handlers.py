import requests
from bs4 import BeautifulSoup
import re
import json
import html
import pymysql
from dotenv import load_dotenv
import os
from makeEmailTemplate import generate_EmailTemplate
from makeCampaign import makeCampaign
from increaseEmailCount import increaseCount

load_dotenv()

def get_db_connection():
    try:
        return pymysql.connect(
            host=os.getenv('DB_HOST'),
            port=int(os.getenv('DB_PORT')),
            user=os.getenv('DB_USERNAME'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME'),
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

def insert_into_mariadb_cve(cve_details):
    conn = get_db_connection()
    if conn is None:
        return

    try:
        with conn.cursor() as cursor:
            sql = """INSERT INTO ca_cve (cve_number, cve_name, cve_description, cve_pubdate, cve_link, cve_severity) 
                     VALUES (%s, %s, %s, %s, %s, %s)"""
            cursor.execute(sql, (
                cve_details['cve_number'],
                cve_details['cve_name'],
                cve_details['cve_description'],
                cve_details['cve_pubdate'],
                cve_details['cve_link'],
                cve_details['cve_severity']
            ))
            conn.commit()
            print(f"\nInserted CVE details into database: {cve_details['cve_number']}")

            return True
    except Exception as e:
        print(f"Error inserting CVE details into database: {e}")
    finally:
        conn.close()

def exist_check_cve(cve_number):
    conn = get_db_connection()
    if conn is None:
        return False

    try:
        with conn.cursor() as cursor:
            cursor.execute('SELECT 1 FROM ca_cve WHERE cve_number = %s', (cve_number,))
            result = cursor.fetchone()
            print(f"\nChecking existence of {cve_number}: {'Exists' if result else 'Does not exist'}")
            return result is not None
    except Exception as e:
        print(f"Error checking CVE existence in database: {e}")
        return False
    finally:
        conn.close()

def fetch_and_process_cve():
    
    scraped_cve = []
    new_entries= False

    try:
        url = "https://cvefeed.io/rssfeed/latest.xml"
        response = requests.get(url)
        response.raise_for_status()
        rss_content = response.content

        soup = BeautifulSoup(rss_content, 'lxml-xml')
        items = soup.find_all('item')

        for item in items:
            title = item.find('title').text
            link = item.find('link').text
            description_tag = item.find('description').text
            pub_date = item.find('pubDate').text

            cve_number_pattern = r'CVE-\d{4}-\d{4,}'
            cve_number_match = re.search(cve_number_pattern, title)
            cve_number = cve_number_match.group() if cve_number_match else 'N/A'

            # If the CVE number already exists in the database, stop processing further items
            if exist_check_cve(cve_number):
                print(f"\n{cve_number} already exists, stopping further checks.")
                break

            clean_description = re.sub(r'<.*?>', '', description_tag)
            clean_description = html.unescape(clean_description).replace('\n', ' ').replace('\u00a0', ' ').strip()

            unwanted_string = "Visit the link for more details, such as CVSS details, affected products, timeline, and more..."
            if unwanted_string in clean_description:
                clean_description = clean_description.replace(unwanted_string, '').strip()

            severity_match = re.search(r'Severity:\s*(\d+(\.\d+)?)\s*\|\s*(\w+)', clean_description)
            severity = severity_match.group(1) if severity_match else None

            cve_page_response = requests.get(link)
            cve_page_response.raise_for_status()
            cve_page_content = cve_page_response.content

            cve_page_soup = BeautifulSoup(cve_page_content, 'html.parser')
            table = cve_page_soup.find('table', class_='table table-responsive table-bordered table-hover table-condensed')
            description_cell = None
            
            if table:
                description_row = table.find('td', string='Description')
                if description_row:
                    description_cell = description_row.find_next_sibling('td').find_next_sibling('td')

            if description_cell:
                clean_description = description_cell.text.strip()
                clean_description = html.unescape(clean_description).replace('\n', ' ').replace('\u00a0', ' ').strip()
            else:
                print(f"Warning: Description not found for CVE: {cve_number}")
                clean_description = "Description not available"
                
            cve_details = {
                'cve_number': cve_number,
                'cve_name': title.split('- ', 1)[1] if '- ' in title else 'N/A',
                'cve_description': clean_description,
                'cve_pubdate': pub_date,
                'cve_link': link,
                'cve_severity': severity
            }

            # cve_details_json = json.dumps(cve_details, indent=4, ensure_ascii=False)
            # print(cve_details_json)

            if insert_into_mariadb_cve(cve_details):
                scraped_cve.append(cve_details)
                new_entries = True
        
        # print(scraped_cve)
        if new_entries:
            generate_EmailTemplate(scraped_cve)
            # if makeCampaign():
            #     increaseCount()
        else:
            print("\n No New Template Generation & Campaign")

    except requests.exceptions.RequestException as e:
        print(f"Error fetching CVE data: {e}")
    except Exception as e:
        print(f"Error processing CVE data: {e}")

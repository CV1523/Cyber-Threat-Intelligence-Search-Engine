import requests
from bs4 import BeautifulSoup
import re
import json
import html
import os
import pymysql
from dotenv import load_dotenv

load_dotenv()

def insert_into_mariadb_news(news_details):
    try:
        conn = pymysql.connect(
            host=os.getenv('DB_HOST'),
            port=int(os.getenv('DB_PORT')),
            user=os.getenv('DB_USERNAME'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME'),
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )

        cursor = conn.cursor()

        sql = "INSERT INTO ca_news (news_title, news_description, news_link, news_pubdate, news_bannerUrl) VALUES (%s,%s,%s,%s,%s)"

        val = (
            news_details['NEWS_TITLE'],
            news_details['news_description'],
            news_details['news_link'],
            news_details['news_pubDate'],
            news_details['news_ImgLink']
        )

        cursor.execute(sql,val)

        conn.commit()

        print(f"Inserted NEWS details into database: {news_details['NEWS_TITLE']}")

    except Exception as e:
        print(f"Error inserting NEWS: {e}")

    finally:
        cursor.close()
        conn.close()
 
def exist_check_news(new_pubDate):
    try:
        conn = pymysql.connect(
            host=os.getenv('DB_HOST'),
            port=int(os.getenv('DB_PORT')),
            user=os.getenv('DB_USERNAME'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME'),
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )

        cursor = conn.cursor()

        cursor.execute('SELECT 1 FROM ca_news WHERE news_pubdate = %s', (new_pubDate,))

        exists = cursor.fetchone() is not None

        return exists
    
    except Exception as e:
        print(f"Error existing check NEWS details from database: {e}")

    finally:
        cursor.close()
        conn.close()

def fetchNews():
    try:
        url = "https://feeds.feedburner.com/TheHackersNews"
        response = requests.get(url)

        if response.status_code==200:
            rss_content = response.content

            soup = BeautifulSoup(rss_content, 'lxml-xml')

            first_item = soup.find('item')

            title = first_item.find('title').text
            # description = first_item.find('description').text
            link = first_item.find('link').text
            pub_date = first_item.find('pubDate').text
            enclosure = first_item.find('enclosure')
            enclosure_url = enclosure['url'] if enclosure else None

            clean_title = html.unescape(title).replace('\n',' ').replace('\"',' ').replace('\u00a0', ' ').strip()

            news_page_response = requests.get(link)

            if news_page_response.status_code == 200:
                news_page_content = news_page_response.content

                news_page_soup = BeautifulSoup(news_page_content, 'html.parser')

                paragraph = news_page_soup.find('div', id='articlebody').find('p').get_text()

                clean_description = html.unescape(paragraph).replace('\n',' ').replace('\"',' ').replace('\u00a0', ' ').strip()
                

                news_details = {
                    'NEWS_TITLE':clean_title,
                    'news_description': clean_description,
                    'news_link':link,
                    'news_pubDate':pub_date,
                    'news_ImgLink': enclosure_url
                }

                news_details_json = json.dumps(news_details, indent=4, ensure_ascii=False)

                # return news_details_json
                print(news_details_json)

                if not (exist_check_news(news_details['news_pubDate'])):
                    insert_into_mariadb_news(news_details)
                else:
                    print(f"{news_details['news_pubDate']} Already Exist")

            else:
                print("Failed Fetching Description")
    except Exception as e:
        print(f"Failed Fetching News: {e}")

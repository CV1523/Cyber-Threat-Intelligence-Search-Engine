import os
import pymysql
from dotenv import load_dotenv
from datetime import datetime

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

def increaseCount():
    conn = get_db_connection()
    today_date = datetime.now().strftime('%Y-%m-%d')
    if conn is None:
        return

    try:
        with conn.cursor(dictionary=True) as cursor:
            
            sql = f"SELECT * FROM ca_cve_emailSentCount WHERE cve_campaignDate = '{today_date}';"
            cursor.execute(sql)

            entryExist = cursor.fetchone()

            if not entryExist:
                new_sql_CountEntry = """
                    INSERT INTO ca_cve_emailSentCount (cve_campaignDate, campaignSentCount) VALUES (%s, 1)
                """
                cursor.execute(new_sql_CountEntry, (today_date,))
                conn.commit()
            else:
                update_sql_CountEntry = """
                    UPDATE ca_cve_emailSentCount SET campaignSentCount = %s WHERE cve_campaignDate = %s
                """
                new_count = entryExist['campaignSentCount'] + 1
                cursor.execute(update_sql_CountEntry, (new_count, today_date))
                conn.commit()
            
            print(f"\nIncreased Email Count on: {today_date}")
    except Exception as e:
        print(f"Error Increasing Email Count in the database: {e}")
    finally:
        conn.close()

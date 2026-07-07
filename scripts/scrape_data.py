import cloudscraper
from bs4 import BeautifulSoup
import time
import random
import pandas as pd
import logging
import os
import json
from dotenv import load_dotenv

from src.database_helper import NovelDB
from scripts.data_cleaning import cleaning_pipeline

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scraper = cloudscraper.create_scraper(
    browser={
        'browser': 'chrome',
        'platform': 'windows',
        'mobile': False
    }
)
cookies_str = os.getenv('NU_COOKIES')
if cookies_str:
    cookies = json.loads(cookies_str)
else:
    logger.warning("No cookies found in environment variables")
    cookies = {}

def scrape_novel(novel_url):
    try:
        response = scraper.get(novel_url, cookies=cookies)
        if response.status_code != 200:
            logger.error(f"Failed to retrieve novel: {novel_url}")
            return None
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        description_tag = soup.select('div#editdescription p')
        description = ' '.join([p.text.strip() for p in description_tag]) if description_tag else ""
        
        genres_tag = soup.select('div#seriesgenre a')
        genres = [genre.text.strip() for genre in genres_tag] or []
        
        tags_tag = soup.select('div#showtags a')
        tags = [tag.text.strip() for tag in tags_tag] or []

        rec_block = None
        for h5 in soup.find_all("h5", class_="seriesother"):
            if "Recommendations" in h5.get_text():
                rec_block = h5
                break
            
        link = None
        if rec_block:
            rec_link = rec_block.find("a")
            if rec_link is not None:
                link = str(rec_link['href'])
                if link.startswith("//"):
                    link = "https:" + link        

        return {
            "description": description,
            "genres": genres,
            "tags": tags,
            "recommendations_link": link
        }
    except Exception as e:
        logger.exception(f"Error scraping {novel_url}: {e}")
        return None
    
def get_novel_details(db_manager, batch_size=50, limit=100):
    logger.info("Starting novel details extraction.")
    
    novels = db_manager.get_skeleton_novels(limit=limit)
    total = len(novels)
    
    if total == 0:
        logger.info("No skeleton novels found.")
        return
    
    logger.info(f"Processing {total} novels in batches of {batch_size}")
    
    for i in range(0, total, batch_size):
        batch = novels[i:i + batch_size]
        novel_details = []
        recs_links = []
        logger.info(f"\nProcessing batch {i//batch_size + 1}")
        
        for novel in batch:
            details = scrape_novel(novel.link)
            if details:
                novel_details.append({
                    "title": novel.title,
                    "link": novel.link,
                    "description": details['description'],
                    "genres": details['genres'],
                    "tags": details['tags'],
                })
                if details['recommendations_link']:
                    recs_links.append({
                            "id": novel.id,
                            "rec_link": details['recommendations_link']
                        })
            time.sleep(random.uniform(2, 5))
        
        if novel_details:
            logger.info(f"Cleaning and adding {len(novel_details)} novels to DB")
            df = cleaning_pipeline(pd.DataFrame(novel_details), min_tag_count=10)
            db_manager.add_novels(df)
            
        if recs_links:
            logger.info(f"Processing {len(recs_links)} recommendation links")
            store_recommedations(recs_links, db_manager)
        
        logger.info(f"Batch {i//batch_size + 1} done.")
        time.sleep(random.uniform(7, 10))

def scrape_recommendations(url):
    try:
        response = scraper.get(url)
        if response.status_code != 200:
            logger.error(f"Failed to retrive recommendation page: {url}")
            return None
        
        soup = BeautifulSoup(response.content, 'html.parser')
        recommendations = []
        for a in soup.select("span.rec_list + a"):
            recommendations.append({
                "title": a.text.strip(),
                "link": a['href']
            })
        return recommendations if recommendations else None
    except Exception as e:
        logger.error(f"Error scraping recommendations from {url}: {e}")
        return None
    
def store_recommedations(recs_links, db_manager):
    logger.info(f"Storing recommendations for {len(recs_links)} novels")
    
    processed = 0
    failed = 0
    not_found = 0
    for novel in recs_links:
        try:
            link = novel['rec_link']
            idx = novel['id']
            
            recommendations = scrape_recommendations(link)
            if recommendations:
                db_manager.add_recommendations(idx, recommendations)
                processed += 1
            else:
                not_found+=1
        except Exception as e:
            logger.exception(f"Error storing recommendations for novel {idx}: {e}")
            failed += 1
        time.sleep(random.uniform(2, 5))
    logger.info(f"Processed: {processed}, Failed: {failed}, Recs not found: {not_found}")
    time.sleep(random.uniform(7, 10))
    
# if __name__ == "__main__":
#     logger.info("Starting novel scraping pipeline...")
#     db = NovelDB()
#     logger.info(f"Database initialized. Current count: {db.get_stats()}")

#     get_novel_details(db, batch_size=50, limit=50)
#     logger.info("Scraping complete!")
#     logger.info(f"Final stats: {db.get_stats()}")
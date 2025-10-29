import cloudscraper
from bs4 import BeautifulSoup
import json
import time
import random

scraper = cloudscraper.create_scraper(
    browser={
        'browser': 'chrome',
        'platform': 'windows',
        'mobile': False
    }
)

def scrapeList(list_url):
    novels = []
    page = 1
    fail_count = 0
    while True:
        url = f"{list_url}?st=1&pg={page}"
        try:
            response = scraper.get(url)
        except Exception as e:
            print(f"Request failed: {e}")
            fail_count += 1
            if fail_count >= 3:
                print("Too many failed attempts.")
                break

        if response.status_code != 200:
            print("Non-200 response, stopping.")
            break

        soup = BeautifulSoup(response.content, 'html.parser')
        novel_entries = soup.find_all('div', class_='search_body_nu')
        if not novel_entries:
            break
        for entry in novel_entries:
            title_tag = entry.select_one('div.search_title a span')
            link_tag = entry.select_one("div.search_title a")
            novels.append({
                "title" : title_tag.text.strip() if title_tag else None,
                "link" : link_tag['href'] if link_tag else None
            })
        print(f"page {page} of {list_url} done")
        page += 1
        time.sleep(random.uniform(1.5, 4)) 
    return novels

def getNovelsList(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        lists = [line.strip() for line in f]

    output_path = "data/raw/novels_list.json"
    all_novels = []
    existing_links = set()

    try:
        with open(output_path, 'r', encoding='utf-8') as f:
            all_novels = json.load(f)
            existing_links = {novel['link'] for novel in all_novels if novel.get("link")}
    except FileNotFoundError:
        # create a damn file
        pass
    except json.JSONDecodeError:
        all_novels = []
        existing_links = set()
        
    for url in lists:
        try:
            new_novels = scrapeList(url)
            for novel in new_novels:
                if novel['link'] not in existing_links:
                    all_novels.append(novel)
                    existing_links.add(novel['link'])
            with open('data/raw/novels_list.json', 'w', encoding='utf-8') as f:
                json.dump(all_novels, f, ensure_ascii=False,)
            print(f"{url} done")
            time.sleep(random.uniform(1.5, 4.5))
        except Exception as e:
            print(f"Error scraping {url}: {e}")
        time.sleep(5)

def scrapeNovel(novel_url):
    try:
        response = scraper.get(novel_url)
        if response.status_code != 200:
            print(f"Failed to retrieve novel: {novel_url}")
            return None
        soup = BeautifulSoup(response.content, 'html.parser')
        description_tag = soup.select('div#editdescription p')
        genres_tag = soup.select('div#seriesgenre a')
        tags_tag = soup.select('div#showtags a')
        description = ' '.join([p.text.strip() for p in description_tag]) if description_tag else ""
        genres = [genre.text.strip() for genre in genres_tag] or []
        tags = [tag.text.strip() for tag in tags_tag] or []

        return {
            "description": description,
            "genres": genres,
            "tags": tags
        }
    except Exception as e:
        print(f"Error scraping {novel_url}: {e}")
        return None
    
def getNovelDetails(list_file, novel_file, batch_size=50):
    with open(list_file, 'r', encoding='utf-8') as f:
        novels_list = json.load(f)

    novel_details = []
    scraped_links = set()
    try:
        with open(novel_file,'r',encoding='utf-8') as f:
            novel_details = json.load(f)
            scraped_links = {novel['link'] for novel in novel_details if novel.get("link")}
    except FileNotFoundError:
        print("Novel details file not found.")
    except json.JSONDecodeError:
        novel_details = []
        scraped_links = set()
        
    total = len(novels_list)
    for i in range(0, total, batch_size):
        batch = novels_list[i:i + batch_size]
        for novel in batch:
            if novel['link'] in scraped_links:
                continue
            details = scrapeNovel(novel['link'])
            if details:
                novel_details.append({
                    "title": novel['title'],
                    "link": novel['link'],
                    **details
                })
                scraped_links.add(novel['link'])
            time.sleep(random.uniform(2, 5))
        with open(novel_file,'w',encoding='utf-8') as f:
            json.dump(novel_details,f,ensure_ascii=False,)
            print(f"Batch {i//batch_size + 1} done.")
        time.sleep(random.uniform(7, 10))
     
getNovelsList('data/raw/novel_lists.txt')   
getNovelDetails("data/raw/novels_list.json","data/raw/novel_details.json", batch_size=50)
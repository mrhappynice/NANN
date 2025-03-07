import requests
import sqlite3
import datetime
from bs4 import BeautifulSoup
import re
import threading
import time
import spacy

# -------------------------------
# Setup spaCy model (ensure you have installed en_core_web_sm)
# Run: python -m spacy download en_core_web_sm
# -------------------------------
nlp = spacy.load("en_core_web_sm")

# -------------------------------
# Database Handler for SQLite
# -------------------------------
class DatabaseHandler:
    def __init__(self, db_name="research_assistant.db"):
        self.db_name = db_name
        self.conn = sqlite3.connect(self.db_name)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        # Create Sources table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE,
                domain TEXT,
                crawl_date TEXT,
                credibility TEXT
            );
        """)
        # Create Content table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER,
                content TEXT,
                keywords TEXT,
                FOREIGN KEY(source_id) REFERENCES Sources(id)
            );
        """)
        self.conn.commit()

    def insert_source(self, url, domain, credibility):
        cursor = self.conn.cursor()
        crawl_date = datetime.datetime.now().isoformat()
        try:
            cursor.execute("""
                INSERT INTO Sources (url, domain, crawl_date, credibility)
                VALUES (?, ?, ?, ?);
            """, (url, domain, crawl_date, credibility))
            self.conn.commit()
        except sqlite3.IntegrityError:
            # URL already exists, update the crawl_date if needed.
            cursor.execute("""
                UPDATE Sources SET crawl_date = ? WHERE url = ?;
            """, (crawl_date, url))
            self.conn.commit()
        return cursor.lastrowid

    def insert_content(self, source_id, content, keywords):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO Content (source_id, content, keywords)
            VALUES (?, ?, ?);
        """, (source_id, content, keywords))
        self.conn.commit()

# -------------------------------
# Parser Module using BeautifulSoup
# -------------------------------
class Parser:
    def parse(self, html):
        soup = BeautifulSoup(html, "html.parser")
        # Extract content from <p> and <article> tags.
        texts = []
        for tag in soup.find_all(["p", "article"]):
            text = tag.get_text(separator=" ", strip=True)
            if text:
                texts.append(text)
        return "\n".join(texts)

# -------------------------------
# Concept Extraction Module using spaCy
# -------------------------------
class ConceptExtractor:
    def extract_keywords(self, text):
        doc = nlp(text)
        keywords = set()
        for ent in doc.ents:
            if ent.label_ in ["ORG", "PERSON", "GPE", "DATE", "EVENT", "PRODUCT"]:
                keywords.add(ent.text)
        return list(keywords)

# -------------------------------
# Crawler Module
# -------------------------------
class Crawler:
    def __init__(self, db_handler, depth_limit=1):
        self.db_handler = db_handler
        self.depth_limit = depth_limit
        self.parser = Parser()
        self.extractor = ConceptExtractor()

    def get_domain(self, url):
        return re.sub(r'^www\.', '', url.split("//")[-1].split("/")[0])

    def assign_credibility(self, domain):
        if domain.endswith(".gov") or domain.endswith(".edu"):
            return "high credibility"
        else:
            return "general"

    def crawl_url(self, url, current_depth=0):
        if current_depth > self.depth_limit:
            return

        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                html = response.text
                content = self.parser.parse(html)
                domain = self.get_domain(url)
                credibility = self.assign_credibility(domain)
                source_id = self.db_handler.insert_source(url, domain, credibility)
                keywords = self.extractor.extract_keywords(content)
                self.db_handler.insert_content(source_id, content, ", ".join(keywords))
                print(f"Crawled: {url}")
                if current_depth < self.depth_limit:
                    soup = BeautifulSoup(html, "html.parser")
                    links = {a['href'] for a in soup.find_all("a", href=True) if a['href'].startswith("http")}
                    for link in links:
                        self.crawl_url(link, current_depth + 1)
            else:
                print(f"Failed to retrieve {url}: Status code {response.status_code}")
        except Exception as e:
            print(f"Error crawling {url}: {e}")

    def crawl(self, urls):
        for url in urls:
            self.crawl_url(url)

# -------------------------------
# Updater Module (continuous crawler)
# -------------------------------
class Updater:
    def __init__(self, crawler, update_interval=86400):  # default 24 hours
        self.crawler = crawler
        self.update_interval = update_interval
        self._stop_event = threading.Event()

    def start(self, urls):
        def run_updates():
            while not self._stop_event.is_set():
                print("Starting scheduled update...")
                self.crawler.crawl(urls)
                print("Update completed. Sleeping until next update.")
                time.sleep(self.update_interval)
        threading.Thread(target=run_updates, daemon=True).start()

    def stop(self):
        self._stop_event.set()

# -------------------------------
# Main function for crawler
# -------------------------------
def main():
    db_handler = DatabaseHandler()

    urls = [
        "https://example.com",
        "https://example.gov",
        "https://example.edu"
    ]

    crawler = Crawler(db_handler, depth_limit=1)
    # Run an initial crawl
    crawler.crawl(urls)

    # Uncomment to enable continuous updates (every 24 hours)
    # updater = Updater(crawler, update_interval=86400)
    # updater.start(urls)

if __name__ == "__main__":
    main()

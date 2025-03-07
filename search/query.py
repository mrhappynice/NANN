import argparse
import sqlite3
import os
from openai import OpenAI

# -------------------------------
# Database Handler (reuse from crawler)
# -------------------------------
class DatabaseHandler:
    def __init__(self, db_name="research_assistant.db"):
        self.db_name = db_name
        self.conn = sqlite3.connect(self.db_name)

    def fetch_all_content(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT Sources.url, Sources.domain, Sources.credibility, Content.content, Content.keywords
            FROM Content
            JOIN Sources ON Content.source_id = Sources.id;
        """)
        return cursor.fetchall()

# -------------------------------
# Configurable LLM Client using the new OpenAI client syntax
# -------------------------------
class LLMClient:
    def __init__(self, model_name="gpt-4o-mini", api_key=None, api_url="https://api.openai.com/v1", use_chat=True):
        self.model_name = model_name
        self.use_chat = use_chat
        if api_key is None:
            api_key = os.getenv("OPENAI_API_KEY")
        # Pass the API URL to the OpenAI client as the base_url.
        self.client = OpenAI(api_key=api_key, base_url=api_url)
    
    def summarize(self, text, max_tokens=150):
        if self.use_chat:
            messages = [
                {"role": "system", "content": "You are a summarization assistant."},
                {"role": "user", "content": f"Please summarize the following content:\n\n{text}"}
            ]
            chat_completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.5,
            )
            return chat_completion.choices[0].message.content.strip()
        else:
            prompt = f"You are a summarization assistant. Please summarize the following content:\n\n{text}"
            completion = self.client.completions.create(
                model=self.model_name,
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=0.5,
            )
            return completion.choices[0].text.strip()
    
    def query(self, prompt, max_tokens=150):
        if self.use_chat:
            messages = [
                {"role": "system", "content": "You are an assistant that helps answer queries based on provided research data."},
                {"role": "user", "content": prompt}
            ]
            chat_completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.5,
            )
            return chat_completion.choices[0].message.content.strip()
        else:
            combined_prompt = ("You are an assistant that helps answer queries based on provided research data.\n\n" +
                               prompt)
            completion = self.client.completions.create(
                model=self.model_name,
                prompt=combined_prompt,
                max_tokens=max_tokens,
                temperature=0.5,
            )
            return completion.choices[0].text.strip()

# -------------------------------
# Query Interface for Database Augmentation
# -------------------------------
class QueryInterface:
    def __init__(self, db_handler, llm_client):
        self.db_handler = db_handler
        self.llm_client = llm_client

    def build_context(self):
        data = self.db_handler.fetch_all_content()
        context_lines = []
        for row in data:
            url, domain, credibility, content, keywords = row
            snippet = content[:300] + "..."
            context_lines.append(f"Source: {url}\nSnippet: {snippet}\nKeywords: {keywords}\n")
        return "\n".join(context_lines)

    def answer_query(self, user_query):
        context = self.build_context()
        prompt = f"Using the following research data:\n\n{context}\n\nAnswer the following query:\n{user_query}"
        result = self.llm_client.query(prompt)
        return result

def main():
    parser = argparse.ArgumentParser(description="LLM Augmented Query Assistant")
    parser.add_argument("--query", type=str, required=True,
                        help="User query to run against the research database.")
    parser.add_argument("--model", type=str, default="gpt-4o-mini",
                        help="Model name to use (default: gpt-4o-mini).")
    parser.add_argument("--api_url", type=str, default="https://api.openai.com/v1",
                        help="The base URL for the OpenAI API (default: https://api.openai.com/v1).")
    parser.add_argument("--use_chat", dest="use_chat", action="store_true",
                        help="Use chat completions endpoint (default behavior).")
    parser.add_argument("--no_chat", dest="use_chat", action="store_false",
                        help="Use completions endpoint instead of chat completions.")
    parser.set_defaults(use_chat=True)
    args = parser.parse_args()

    llm_client = LLMClient(model_name=args.model, api_url=args.api_url, use_chat=args.use_chat)
    db_handler = DatabaseHandler()
    query_interface = QueryInterface(db_handler, llm_client)

    answer = query_interface.answer_query(args.query)
    print("LLM Augmented Answer:")
    print(answer)

if __name__ == "__main__":
    main()

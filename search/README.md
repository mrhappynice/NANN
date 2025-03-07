# NANN - search

Setup:
```bash
pip install requests beautifulsoup4 spacy openai
python -m spacy download en_core_web_sm
```

Run:
```bash
python3 query.py --query "what is this business?" --model "gpt-4o-mini"

```

Check options in query.py, setup your favorite OAI-ish endpoint. 

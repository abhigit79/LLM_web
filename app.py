import streamlit as st
from newspaper import Article
import google.generativeai as genai
import requests
from concurrent.futures import ThreadPoolExecutor
import re
import os
from dotenv import load_dotenv

load_dotenv(override=True)
api_key = os.getenv('API_KEY')
CSE_API_KEY = os.getenv('CSE_API_KEY')
CSE_ID = os.getenv('CSE_ID')
GENAI_API_KEY = os.getenv('GOOGLE_API_KEY')


# Configure GenAI
genai.configure(api_key=GENAI_API_KEY)


def clean_text(text):
    """Clean and truncate text"""
    text = re.sub(r'\s+', ' ', text)
    return text[:5000]


def scrape_article(url):
    """Scrape and parse article content"""
    try:
        article = Article(url)
        article.download()
        article.parse()
        return clean_text(article.text)
    except Exception as e:
        print(f"Error scraping {url}: {str(e)}")
        return None


def google_search(query, num_results=50):
    """Use Google Custom Search JSON API"""
    try:
        results = []
        max_per_page = 10  # Google API max per request
        pages = (num_results // max_per_page) + 1

        for page in range(pages):
            start = page * max_per_page + 1
            url = f"https://www.googleapis.com/customsearch/v1?key={CSE_API_KEY}&cx={CSE_ID}&q={query}&start={start}&num={max_per_page}"
            response = requests.get(url).json()
            results += [item['link'] for item in response.get('items', [])]
            if len(results) >= num_results:
                break

        return results[:num_results]
    except Exception as e:
        st.error(f"Search API error: {str(e)}")
        return []


def search_and_scrape(query, num_results=50):
    """Search and scrape results"""
    search_results = google_search(query, num_results)

    with ThreadPoolExecutor(max_workers=10) as executor:
        contents = list(executor.map(scrape_article, search_results))

    return [text for text in contents if text is not None]


def generate_response(query, context):
    """Generate response using Gemini"""
    model = genai.GenerativeModel('gemini-pro')

    # Calculate number of sources first
    num_sources = len(context.split('\n\n'))

    # Create formatted prompt without backslashes
    prompt = (
        f"Analyze this information from {num_sources} websites and provide "
        f"a comprehensive answer to: {query}\n\n"
        "Web Content:\n"
        f"{context}\n\n"
        "Answer in detail with proper formatting:"
    )

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Generation error: {str(e)}"


# Streamlit UI
st.title("🔍 Smart Search Assistant")
query = st.text_input("Enter your question:", placeholder="Ask anything...")
num_results = st.slider("Number of results to analyze:", 10, 100, 50)

if st.button("Search") or query:
    if not query:
        st.warning("Please enter a question")
        st.stop()

    with st.spinner("Searching the web..."):
        articles = search_and_scrape(query, num_results)

    if not articles:
        st.error("No articles found. Try a different query.")
        st.stop()

    context = "\n\n".join(articles)[:30000]

    with st.spinner("Analyzing results..."):
        response = generate_response(query, context)

    st.subheader("Research Summary")
    st.markdown(response)

    with st.expander("View raw context"):
        st.write(context[:10000] + "...")
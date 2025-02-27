import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from urllib.parse import urljoin, urlparse
import time
import os

# Global variables
visited_urls = set()  # Tracks visited pages
external_links = []  # Stores external links and their sources

# List of file extensions to skip
SKIP_EXTENSIONS = [".pdf", ".jpg", ".jpeg", ".png", ".gif", ".mp4", ".zip", ".doc", ".docx", ".xls", ".xlsx"]

def should_skip_url(url):
    """Check if the URL points to a file type we want to skip."""
    parsed_url = urlparse(url)
    path = parsed_url.path.lower()
    return any(path.endswith(ext) for ext in SKIP_EXTENSIONS)

def is_valid_landing_page(url):
    """
    Check if the URL is a valid landing page.
    Exclude URLs containing '#' or 'et_blog'.
    """
    if "#" in url or "et_blog" in url:
        return False
    return True

def get_links(url, base_url):
    """Fetch all links (internal + external) from a page."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        content_type = response.headers.get("Content-Type", "")
        if "text/html" not in content_type:
            st.warning(f"Skipping non-HTML content: {url}")
            return set()

        soup = BeautifulSoup(response.text, "html.parser")
        internal_links = set()
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            full_url = urljoin(url, href)
            
            if should_skip_url(full_url):
                continue
            if not is_valid_landing_page(full_url):
                continue

            parsed_url = urlparse(full_url)
            if parsed_url.netloc == urlparse(base_url).netloc:
                internal_links.add(full_url)
            elif full_url.startswith("http"):
                external_links.append((full_url, url))
        
        return internal_links
    except requests.RequestException as e:
        st.error(f"Error fetching {url}: {e}")
        return set()

def crawl_website(start_url, progress_bar, status_placeholder, percentage_placeholder):
    """Recursively crawls the entire site to find external links."""
    urls_to_visit = {start_url}
    total_urls_discovered = len(urls_to_visit)
    while urls_to_visit:
        current_url = urls_to_visit.pop()
        if current_url not in visited_urls:
            visited_urls.add(current_url)
            
            progress_value = len(visited_urls) / total_urls_discovered
            progress_bar.progress(min(progress_value, 1.0))
            percentage_placeholder.text(f"{int(progress_value * 100)}% Complete")
            
            status_placeholder.text(f"Crawling: {current_url}")
            
            new_links = get_links(current_url, start_url)
            new_internal_links = new_links - visited_urls - urls_to_visit
            urls_to_visit.update(new_internal_links)
            total_urls_discovered += len(new_internal_links)
            time.sleep(1)

def save_to_csv():
    """Saves external links and their source pages to CSV."""
    df_external_links = pd.DataFrame(external_links, columns=["External Link", "Linked From Page"])
    csv_data = df_external_links.to_csv(index=False).encode('utf-8')
    return csv_data

def export_to_csv():
    """Provides a download link for the CSV file."""
    if external_links:
        csv_data = save_to_csv()
        st.download_button(
            label="Export All to CSV",
            data=csv_data,
            file_name="external_links.csv",
            mime="text/csv"
        )
    else:
        st.warning("No external links found to export.")

def clear_results():
    """Clears the results."""
    global external_links
    external_links = []
    st.experimental_rerun()

# Streamlit App UI
st.set_page_config(page_title="External Links Web Crawler", page_icon="", layout="wide")

# Title and description
st.title("External Links Web Crawler")

# Input field for the base URL
root_url = st.text_input("Enter Root URL (e.g., https://www.bessemeter.com)", placeholder="https://www.example.com").strip()

# Input field for keyword filter
keyword_filter = st.text_input("Enter keyword to filter (e.g., wagner) or Leave empty for all external links", "").strip()

# Start crawling button
if st.button("Start Crawling"):
    if not root_url:
        st.error("Please enter a valid root URL.")
    elif not root_url.startswith("http://") and not root_url.startswith("https://"):
        st.error("The root URL must start with 'http://' or 'https://'.")
    else:
        st.info(f"Starting crawl at: {root_url}")
        
        progress_bar = st.progress(0)
        status_placeholder = st.empty()
        percentage_placeholder = st.empty()
        
        try:
            visited_urls.clear()
            external_links.clear()

            # Start crawling in the background
            crawl_website(root_url, progress_bar, status_placeholder, percentage_placeholder)

            if external_links:
                st.success(f"✅ Crawling completed! Found {len(external_links)} external links.")

                # Filter external links based on keyword
                filtered_links = [(link, source) for link, source in external_links if keyword_filter in link]

                if filtered_links:
                    df_filtered_links = pd.DataFrame(filtered_links, columns=["External Link", "Linked From Page"])
                    st.subheader("External Links Found:")
                    st.dataframe(df_filtered_links)
                else:
                    st.warning("No matching external links found based on the keyword filter.")
            else:
                st.warning("No external links found during the crawl.")
        except Exception as e:
            st.error(f"An error occurred during crawling: {e}")

# Export to CSV button (always visible)
if external_links:
    export_to_csv()
else:
    st.warning("No external links available to export. Start crawling first.")

# Clear Results button (always visible)
if st.button("Clear Results", key="clear_button"):
    clear_results()

# Footer
st.markdown("---")
st.markdown("Any question? contact")
st.markdown("<h2 style='text-align: center;'>jean@goodnewsadvocates.org</h2>", unsafe_allow_html=True)
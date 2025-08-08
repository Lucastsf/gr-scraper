import requests
from bs4 import BeautifulSoup
from collections import Counter
import time
import random
import os
import json
import hashlib
from functools import lru_cache
from datetime import datetime, timedelta
import shutil

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36"
}

# Create cache directory if it doesn't exist
DEFAULT_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache')
CACHE_DIR = os.environ.get('CACHE_DIR', DEFAULT_CACHE_DIR)
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR, exist_ok=True)

# Users file for persistence
DEFAULT_USERS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'users.json')
USERS_FILE = os.environ.get('USERS_FILE', DEFAULT_USERS_FILE)

# Default users used on first run if no users.json exists or cannot be read
DEFAULT_USER_DATA = {
    "Lucas": "149613316",
    "Scott": "181459152",
    "Steeeeeeeeeeeeeeve": "177163782",
    "Saif": "84888953",
    "Dickson": "60267601",
    "Kris": "163608983",
}

# Cache expiration time (in hours)
CACHE_EXPIRATION_HOURS = 24

def get_cache_key(selected_users, min_count):
    """Generate a unique cache key based on the query parameters."""
    # Sort selected users to ensure consistent cache keys
    sorted_users = sorted(selected_users) if selected_users else []
    # Create a string representation of the parameters
    key_str = f"users={','.join(sorted_users)}_min_count={min_count}"
    # Hash the string to create a filename-safe key
    return hashlib.md5(key_str.encode()).hexdigest()

def get_from_cache(cache_key):
    """Retrieve data from the cache if it exists and is not expired."""
    cache_file = os.path.join(CACHE_DIR, f"{cache_key}.json")

    if not os.path.exists(cache_file):
        return None, False

    try:
        with open(cache_file, 'r') as f:
            cache_data = json.load(f)

        # Check if cache is expired
        cache_time = datetime.fromisoformat(cache_data['timestamp'])
        expiration_time = cache_time + timedelta(hours=CACHE_EXPIRATION_HOURS)

        if datetime.now() > expiration_time:
            print(f"Cache expired for key {cache_key}")
            return None, False

        print(f"Cache hit for key {cache_key}")
        return cache_data['data'], True
    except Exception as e:
        print(f"Error reading from cache: {e}")
        return None, False

def save_to_cache(cache_key, data):
    """Save data to the cache with a timestamp."""
    cache_file = os.path.join(CACHE_DIR, f"{cache_key}.json")

    try:
        cache_data = {
            'timestamp': datetime.now().isoformat(),
            'data': data
        }

        with open(cache_file, 'w') as f:
            json.dump(cache_data, f)

        print(f"Saved to cache with key {cache_key}")
        return True
    except Exception as e:
        print(f"Error saving to cache: {e}")
        return False

def request_with_retry(url, max_retries=3, base_delay=1, max_delay=10, timeout=20):
    """Makes a request with exponential backoff retry logic."""
    retries = 0
    while retries <= max_retries:
        try:
            # Add a small random delay to avoid rate limiting
            if retries > 0:
                delay = min(base_delay * (2 ** (retries - 1)) + random.uniform(0, 1), max_delay)
                print(f"Retrying in {delay:.2f} seconds...")
                time.sleep(delay)

            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()

            # Add a small delay between successful requests to be polite
            time.sleep(random.uniform(0.5, 1.5))

            return response
        except requests.exceptions.RequestException as e:
            retries += 1
            print(f"Request failed ({retries}/{max_retries}): {e}")
            if retries > max_retries:
                raise

    return None

def load_users():
    """Load users from the persistent users.json file, falling back to defaults."""
    try:
        with open(USERS_FILE, 'r') as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
            # If stored as list of objects, convert to dict
            if isinstance(data, list):
                converted = {item["name"]: item["id"] for item in data if isinstance(item, dict) and "name" in item and "id" in item}
                if converted:
                    return converted
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"Error loading users: {e}")
    return DEFAULT_USER_DATA.copy()

def save_users(users_mapping):
    """Persist the given users mapping to users.json."""
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
        with open(USERS_FILE, 'w') as f:
            json.dump(users_mapping, f, indent=2, sort_keys=True)
        return True
    except Exception as e:
        print(f"Error saving users: {e}")
        return False

def clear_all_caches():
    """Clear in-memory and file-based caches."""
    try:
        get_to_read_list.cache_clear()
        get_book_page_count.cache_clear()
        shutil.rmtree(CACHE_DIR, ignore_errors=True)
        os.makedirs(CACHE_DIR, exist_ok=True)
        return True
    except Exception as e:
        print(f"Error clearing caches: {e}")
        return False

# Initialize user_data from persistent storage
user_data = load_users()
# Ensure users.json exists on first run
if not os.path.exists(USERS_FILE):
    save_users(user_data)

@lru_cache(maxsize=32)
def get_to_read_list(username, fetch_page_count=False):
    """Fetches the to-read list for a Goodreads user based on their username. Results are cached in memory.

    Args:
        username: The Goodreads user ID
        fetch_page_count: If True, fetches page count for each book. If False, page_count will be None.
    """
    print(f"Fetching to-read list for {username} (not from cache)")
    page = 1
    book_details = []
    base_url = f"https://www.goodreads.com/review/list/{username}?per_page=100&shelf=to-read"

    while True:
        try:
            url = f"{base_url}&page={page}"
            response = request_with_retry(url)

            if response is None:
                print(f"Failed to retrieve data for {username} after multiple retries")
                break

            soup = BeautifulSoup(response.text, 'html.parser')

            books_on_page = soup.select("td.field.title div.value a")
            authors_on_page = soup.select("td.field.author div.value a")

            if not books_on_page:
                break

            for book, author in zip(books_on_page, authors_on_page):
                book_url = f"https://www.goodreads.com{book['href']}"
                page_count = get_book_page_count(book_url) if fetch_page_count else None
                book_details.append({
                    'title': book.text.strip(),
                    'author': author.text.strip(),
                    'page_count': page_count,
                    'url': book_url
                })

            # Check if a "next" page exists
            next_page_link = soup.select_one('a[rel="next"]')
            if not next_page_link:
                break

            page += 1

            # Add a delay between page requests
            time.sleep(random.uniform(1, 2))

        except Exception as e:
            print(f"Failed to retrieve data for {username}: {e}")
            break

    return book_details

@lru_cache(maxsize=128)
def get_book_page_count(book_url):
    """Visits the book page and retrieves the page count, if available. Results are cached."""
    try:
        response = request_with_retry(book_url)

        if response is None:
            print(f"Failed to retrieve details for {book_url} after multiple retries")
            return None

        soup = BeautifulSoup(response.text, 'html.parser')

        # Fetch page count
        page_count_tag = soup.select_one("p[data-testid='pagesFormat']")
        page_count = None
        if page_count_tag:
            page_count_str = page_count_tag.text.split(" pages")[0].strip()
            page_count = int(page_count_str) if page_count_str.isdigit() else None

        return page_count
    except Exception as e:
        print(f"Failed to retrieve details for {book_url}: {e}")

    return None

def find_popular_books_data(user_data, min_count=3, selected_users=None, use_cache=True):
    """Finds books that appear in the to-read lists of multiple users, filtered by min_count, and returns the data.
    Results are cached to disk to speed up future queries with the same parameters.

    This implementation first gets all users' to-read lists without page counts,
    then identifies books that appear in multiple lists (meeting the min_count threshold),
    and only then fetches page counts for those filtered books.
    """
    # If no users are selected, use all users
    if selected_users is None or len(selected_users) == 0:
        selected_users = list(user_data.keys())

    # Check if we have this result in cache
    if use_cache:
        cache_key = get_cache_key(selected_users, min_count)
        cached_data, cache_hit = get_from_cache(cache_key)

        if cache_hit:
            return cached_data

    # If not in cache or cache disabled, fetch the data
    book_count = {}
    processed_users = []
    error_users = []

    # Process each user's data - first pass: get book lists without page counts
    print("Phase 1: Collecting book lists from all users (without page counts)...")
    for username in selected_users:
        try:
            if username in user_data:
                user_id = user_data[username]
                print(f"Fetching data for user {username}...")

                # Add a small delay between user requests to avoid overwhelming the server
                if processed_users:
                    time.sleep(random.uniform(0.5, 1.5))

                # Get books without page counts (faster)
                books = get_to_read_list(user_id, fetch_page_count=False)

                # Process the books for this user
                for book in books:
                    book_key = (book['title'], book['author'])
                    if book_key in book_count:
                        book_count[book_key]['users'].append(username)
                    else:
                        book_count[book_key] = {
                            'title': book['title'],
                            'author': book['author'],
                            'page_count': None,  # Will be populated later for popular books
                            'url': book['url'],
                            'users': [username]
                        }

                processed_users.append(username)
                print(f"Successfully processed data for user {username}")
        except Exception as e:
            error_message = str(e)
            print(f"Error processing data for user {username}: {error_message}")
            error_users.append(username)
            # Continue with other users even if one fails

    # Log summary of processing
    print(f"Processed {len(processed_users)} users successfully: {', '.join(processed_users)}")
    if error_users:
        print(f"Failed to process {len(error_users)} users: {', '.join(error_users)}")

    # Filter books by minimum count
    popular_books = []
    for book_key, book_data in book_count.items():
        if len(book_data['users']) >= min_count:
            popular_books.append(book_data)

    # Sort the popular books by popularity
    popular_books = sorted(popular_books, key=lambda x: len(x['users']), reverse=True)

    # Phase 2: Get page counts only for popular books
    print(f"Phase 2: Fetching page counts for {len(popular_books)} popular books...")
    for i, book in enumerate(popular_books):
        # Add a small delay between requests to avoid overwhelming the server
        if i > 0:
            time.sleep(random.uniform(0.2, 0.5))

        # Fetch the page count for this popular book
        page_count = get_book_page_count(book['url'])
        book['page_count'] = page_count

        # Log progress periodically
        if (i + 1) % 5 == 0 or i == len(popular_books) - 1:
            print(f"Fetched page counts for {i + 1}/{len(popular_books)} popular books")

    # Format the result
    result = []
    for book in popular_books:
        result.append({
            'title': book['title'],
            'author': book['author'],
            'page_count': book['page_count'],
            'url': book['url'],
            'users': book['users'],
            'user_count': len(book['users'])
        })

    print(f"Found {len(result)} books that match the criteria (min_count={min_count})")

    # Log the book list in console
    print("\n======================================================================")
    print("BOOK LIST:")
    print("======================================================================")
    for i, book in enumerate(result):
        print(f"{i+1}. {book['title']} by {book['author']} - {book['page_count']} pages - {book['user_count']} users: {', '.join(book['users'])}")
    print("======================================================================\n")

    # Save results to cache if caching is enabled
    if use_cache:
        cache_key = get_cache_key(selected_users, min_count)
        save_to_cache(cache_key, result)

    return result

def find_popular_books(user_data, min_count=3, selected_users=None):
    """Finds books that appear in the to-read lists of multiple users, filtered by min_count, and prints the results."""
    books = find_popular_books_data(user_data, min_count, selected_users)

    print("======================================================================")
    print("Popular books across lists:")
    for book in books:
        print(f"{book['title']} by {book['author']} - {book['page_count']} pages - {book['user_count']} users: {', '.join(book['users'])}")

# Keep CLI capability
if __name__ == "__main__":
    popular_books = find_popular_books(user_data, min_count=3)

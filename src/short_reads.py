import requests
from bs4 import BeautifulSoup
import time

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36"
}

def get_to_read_list(user_id):
    """Fetches the to-read list for a Goodreads user based on their user ID and retrieves title, author, rating, and book URL."""
    if not user_id:
        print("Error: user_id is None or empty")
        return []

    url = f"https://www.goodreads.com/review/list/{user_id}?shelf=to-read"
    books = []
    page = 1

    while True:
        try:
            # Increased timeout for better reliability
            response = requests.get(f"{url}&page={page}", headers=headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract book details on the current page
            book_rows = soup.select("tr.bookalike.review")
            if not book_rows:
                break

            for row in book_rows:
                try:
                    # Fetch title and URL
                    title_tag = row.select_one("td.field.title div.value a")
                    if not title_tag:
                        continue  # Skip this book if title tag not found

                    try:
                        title = title_tag.text.strip()
                        book_url = f"https://www.goodreads.com{title_tag['href']}"
                    except (AttributeError, KeyError) as e:
                        print(f"Error extracting title/URL: {e}")
                        continue  # Skip this book if title/URL extraction fails

                    # Fetch author name
                    author_tag = row.select_one("td.field.author div.value a")
                    try:
                        author = author_tag.text.strip() if author_tag else "Unknown"
                    except AttributeError:
                        author = "Unknown"  # Default if author extraction fails

                    # Fetch rating
                    rating_tag = row.select_one("td.field.avg_rating div.value")
                    rating = 0.0  # Default rating
                    if rating_tag:
                        try:
                            rating_str = rating_tag.text.strip()
                            rating = float(rating_str)
                        except (ValueError, AttributeError):
                            pass  # Keep default rating if conversion fails

                    # Only add books with valid title and URL
                    if title and book_url:
                        books.append({
                            "title": title,
                            "author": author,
                            "rating": rating,
                            "url": book_url
                        })
                except Exception as e:
                    print(f"Error processing book row: {e}")
                    continue  # Skip this book and continue with the next one

            # Check if a "next" page exists
            next_page_link = soup.select_one('a[rel="next"]')
            if not next_page_link:
                break

            page += 1  # Increment page number for the next request
            time.sleep(1)  # Throttle requests to avoid being blocked

        except requests.exceptions.RequestException as e:
            print(f"Failed to retrieve data for user ID {user_id}: {e}")
            break

    print(f"Total books found for user ID {user_id}: {len(books)}")
    return books

def get_book_page_count(book_url):
    """Visits the book page and retrieves the page count, if available."""
    if not book_url:
        print("Error: book_url is None or empty")
        return None

    try:
        response = requests.get(book_url, headers=headers, timeout=15)  # Increased timeout
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Fetch page count
        page_count_tag = soup.select_one("p[data-testid='pagesFormat']")
        page_count = None
        if page_count_tag:
            page_count_text = page_count_tag.text.strip()
            # Handle different formats: "XXX pages", "XXX Page", etc.
            for word in ["pages", "page", "Pages", "Page"]:
                if word in page_count_text:
                    page_count_str = page_count_text.split(word)[0].strip()
                    if page_count_str.isdigit():
                        page_count = int(page_count_str)
                        break

            # If we still don't have a page count, try to extract any digits
            if page_count is None:
                import re
                digits = re.findall(r'\d+', page_count_text)
                if digits:
                    try:
                        page_count = int(digits[0])
                    except (ValueError, IndexError):
                        pass

        return page_count
    except requests.exceptions.RequestException as e:
        print(f"Failed to retrieve details for {book_url}: {e}")
    except Exception as e:
        print(f"Unexpected error processing {book_url}: {e}")

    # Return None instead of a tuple to prevent TypeError
    return None

def calculate_score(book, default_page_count=200):
    """Calculates a score based on rating and page count, favoring shorter, higher-rated books."""
    try:
        rating = book["rating"]
        # Use default_page_count if page_count is None, not an int, or zero
        page_count = book["page_count"] if isinstance(book["page_count"], int) and book["page_count"] > 0 else default_page_count

        # Ensure we don't divide by zero
        if page_count <= 0:
            page_count = default_page_count

        return rating / page_count
    except Exception as e:
        print(f"Error in calculate_score: {e}")
        return 0.0  # Return a default score on error

def get_top_books(user_id, top_n=10):
    """Gets the top books from a user's to-read list based on a custom scoring system."""
    try:
        books = get_to_read_list(user_id)

        # Check if books is None or empty
        if not books:
            print(f"No books found for user ID {user_id}")
            return []

        # Retrieve page count for each book by visiting individual book pages
        for book in books:
            book["page_count"] = get_book_page_count(book["url"])
            print(f"Retrieved {book['title']} by {book['author']}: Rating = {book['rating']}, Pages = {book['page_count']}")  # Debug output
            time.sleep(1)  # Throttle to avoid overwhelming the server

        # Calculate score for each book
        for book in books:
            try:
                book["score"] = calculate_score(book)
            except Exception as e:
                print(f"Error calculating score for {book['title']}: {e}")
                book["score"] = 0  # Default score if calculation fails

        # Sort books by score in descending order and get the top N books
        # Handle case where there might be fewer books than top_n
        top_books = sorted(books, key=lambda x: x["score"], reverse=True)
        top_books = top_books[:min(top_n, len(top_books))]

        # Print out the top books
        print("Top books based on rating and length:")
        for i, book in enumerate(top_books, start=1):
            print(f"{i}. {book['title']} by {book['author']} - Rating: {book['rating']}, Pages: {book['page_count']}, Score: {book['score']:.4f}")

        return top_books
    except Exception as e:
        print(f"Error in get_top_books: {e}")
        return []  # Return empty list on error


# Run the function for a specific user ID
if __name__ == "__main__":
    user_id = "149613316"  # Replace with the actual Goodreads user ID
    get_top_books(user_id, 50)

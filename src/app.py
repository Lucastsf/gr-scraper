from flask import Flask, render_template, request, jsonify, Response, stream_with_context
import bookclub
import short_reads
import json
import time
import logging
from datetime import datetime
import os

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/clear_cache', methods=['POST'])
def clear_cache():
    """Clears the server-side cache."""
    try:
        # Clear the in-memory cache for get_to_read_list and get_book_page_count
        bookclub.get_to_read_list.cache_clear()
        bookclub.get_book_page_count.cache_clear()

        # Clear the file-based cache
        import shutil
        import os
        shutil.rmtree(bookclub.CACHE_DIR, ignore_errors=True)
        os.makedirs(bookclub.CACHE_DIR, exist_ok=True)

        logger.info("Cache cleared successfully")
        return jsonify({"status": "success", "message": "Cache cleared successfully"})
    except Exception as e:
        logger.error(f"Error clearing cache: {str(e)}")
        response = jsonify({"status": "error", "message": f"Error clearing cache: {str(e)}"})
        response.status_code = 500
        return response

@app.route('/users', methods=['GET'])
def list_users():
    """Return the current set of users as a list of objects."""
    try:
        users = [{"name": name, "id": uid} for name, uid in bookclub.user_data.items()]
        response = jsonify({"users": users})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response
    except Exception as e:
        logger.error(f"Error listing users: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/users', methods=['POST'])
def add_user():
    """Add a new user. Body: {"name": str, "id": str}"""
    try:
        data = request.get_json(force=True, silent=True) or {}
        name = (data.get('name') or '').strip()
        user_id = (data.get('id') or '').strip()
        if not name or not user_id:
            return jsonify({"error": "Both 'name' and 'id' are required"}), 400
        if name in bookclub.user_data:
            return jsonify({"error": "A user with that name already exists"}), 400

        # Update in-memory mapping and persist
        bookclub.user_data[name] = user_id
        if not bookclub.save_users(bookclub.user_data):
            # Rollback if save failed
            bookclub.user_data.pop(name, None)
            return jsonify({"error": "Failed to save users"}), 500

        # Clear caches as the result set may change with new users
        bookclub.clear_all_caches()

        users = [{"name": n, "id": uid} for n, uid in bookclub.user_data.items()]
        response = jsonify({"users": users, "status": "created"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response, 201
    except Exception as e:
        logger.error(f"Error adding user: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/users', methods=['DELETE'])
def delete_users():
    """Delete one or more users. Body can be {"name": str} or {"names": [str, ...]}"""
    try:
        data = request.get_json(force=True, silent=True) or {}
        names = []
        if 'names' in data and isinstance(data['names'], list):
            names = [str(n).strip() for n in data['names'] if str(n).strip()]
        elif 'name' in data:
            one = str(data['name']).strip()
            if one:
                names = [one]

        if not names:
            return jsonify({"error": "Provide 'name' or 'names' to delete"}), 400

        deleted = []
        for name in names:
            if name in bookclub.user_data:
                bookclub.user_data.pop(name, None)
                deleted.append(name)
        if deleted:
            if not bookclub.save_users(bookclub.user_data):
                return jsonify({"error": "Failed to save users after deletion"}), 500
            # Clear caches since the user set changed
            bookclub.clear_all_caches()

        users = [{"name": n, "id": uid} for n, uid in bookclub.user_data.items()]
        response = jsonify({"users": users, "deleted": deleted})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response
    except Exception as e:
        logger.error(f"Error deleting users: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/get_popular_books', methods=['GET'])
def get_popular_books():
    min_count = request.args.get('min_count', 3, type=int)
    selected_users = request.args.getlist('users')
    use_cache = request.args.get('use_cache', 'true').lower() == 'true'

    # Log request information
    logger.info(f"Received request for popular books with min_count={min_count}, users={selected_users}, use_cache={use_cache}")

    try:
        # Check if we have this result in cache
        cache_key = bookclub.get_cache_key(selected_users, min_count)
        cached_data, cache_hit = bookclub.get_from_cache(cache_key) if use_cache else (None, False)

        if cache_hit:
            # Data found in cache
            popular_books = cached_data
            from_cache = True
            logger.info(f"Returning cached data for key {cache_key}")

            # Log the book list in console when retrieved from cache
            print("\n======================================================================")
            print("BOOK LIST (from cache):")
            print("======================================================================")
            for i, book in enumerate(popular_books):
                print(f"{i+1}. {book['title']} by {book['author']} - {book['page_count']} pages - {book['user_count']} users: {', '.join(book['users'])}")
            print("======================================================================\n")
        else:
            # Get popular books data
            popular_books = bookclub.find_popular_books_data(
                bookclub.user_data, 
                min_count=min_count, 
                selected_users=selected_users,
                use_cache=use_cache
            )
            from_cache = False

        # Create response with metadata and CORS headers
        response_data = {
            'books': popular_books,
            'metadata': {
                'from_cache': from_cache,
                'cache_key': cache_key if use_cache else None,
                'timestamp': datetime.now().isoformat()
            }
        }

        response = jsonify(response_data)
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')

        # Log success
        logger.info(f"Successfully processed request, returning {len(popular_books)} books (from_cache={from_cache})")

        return response
    except Exception as e:
        # Log error
        logger.error(f"Error processing request: {str(e)}")

        # Return error response
        response = jsonify({"error": str(e)})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.status_code = 500
        return response

@app.route('/get_top_books', methods=['GET'])
def get_top_books():
    username = request.args.get('username')

    # Log request information
    logger.info(f"Received request for top books for user: {username}")

    try:
        if not username or username not in bookclub.user_data:
            return jsonify({"error": "Invalid or missing username"}), 400

        user_id = bookclub.user_data[username]

        # Get top 50 books for the user
        books = []

        # Call the get_top_books function from short_reads.py
        top_books = short_reads.get_top_books(user_id, top_n=50)

        # Format the books for the response
        for i, book in enumerate(top_books, start=1):
            books.append({
                'title': book['title'],
                'author': book['author'],
                'rating': book['rating'],
                'page_count': book['page_count'],
                'score': book['score'],
                'url': book['url'],
                'rank': i
            })

        # Log success
        logger.info(f"Successfully retrieved {len(books)} top books for user {username}")

        # Create response with CORS headers
        response = jsonify(books)
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')

        return response
    except Exception as e:
        # Log error
        logger.error(f"Error processing request: {str(e)}")

        # Return error response
        response = jsonify({"error": str(e)})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.status_code = 500
        return response

if __name__ == '__main__':
    # Increase timeout and configure server for better handling of long requests
    port = int(os.environ.get('PORT', 5001))
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', debug=debug, port=port, threaded=True, 
            use_reloader=False)  # Disable reloader to avoid duplicate processes

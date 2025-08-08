import bookclub

def test_find_popular_books():
    """Test the find_popular_books_data function with the new two-phase approach."""
    print("Testing find_popular_books_data with two-phase approach...")
    
    # Use a smaller subset of users for testing
    test_user_data = {
        "Lucas": "149613316",
        "Scott": "181459152",
    }
    
    # Set min_count to 1 to ensure we get some results
    min_count = 1
    
    # Disable caching for testing
    use_cache = False
    
    # Call the function
    print("Calling find_popular_books_data...")
    popular_books = bookclub.find_popular_books_data(
        test_user_data, 
        min_count=min_count, 
        use_cache=use_cache
    )
    
    # Print the results
    print(f"Found {len(popular_books)} popular books:")
    for i, book in enumerate(popular_books[:5]):  # Show only first 5 books
        print(f"{i+1}. {book['title']} by {book['author']} - {book['page_count']} pages - {book['user_count']} users: {', '.join(book['users'])}")
    
    if len(popular_books) > 5:
        print(f"... and {len(popular_books) - 5} more books")
    
    print("Test completed successfully!")

if __name__ == "__main__":
    test_find_popular_books()
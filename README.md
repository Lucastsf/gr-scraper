# Goodreads Book Club Frontend

This is a web-based frontend for the Goodreads scraper that displays popular books across multiple users' to-read lists.

## Features

- View popular books that appear in multiple users' to-read lists
- Filter books by minimum number of users
- Sort books by popularity, title, author, or page count
- Responsive design that works on desktop and mobile devices

## Requirements

- Python 3.6+
- Flask
- BeautifulSoup4
- Requests

## Installation


1. Make sure you have Python and pip installed:
   - Python can be downloaded from [python.org](https://www.python.org/downloads/)
   - pip is included with Python installations from Python 3.4 onwards

2. Verify your Python installation by running one of these commands in your terminal:

```bash
# On macOS and most Linux systems:
python3 --version

# On Windows or if python3 command doesn't work:
python --version
```

3. Create a virtual environment (recommended to avoid system package conflicts):

```bash
# On macOS and most Linux systems:
python3 -m venv venv

# On Windows or if python3 command doesn't work:
python -m venv venv
```

4. Activate the virtual environment:

```bash
# On macOS and most Linux systems:
source venv/bin/activate

# On Windows (Command Prompt):
venv\Scripts\activate.bat

# On Windows (PowerShell):
venv\Scripts\Activate.ps1
```

5. Install the required packages in the virtual environment:

```bash
pip install flask beautifulsoup4 requests
```

   Note: Modern macOS and many Linux distributions use `python3` for Python 3.x and reserve `python` for Python 2.x (which may not be installed). Windows typically uses `python` for the latest installed version. When a virtual environment is activated, you can use `python` and `pip` commands directly without version suffixes.

## Usage

1. Ensure your virtual environment is activated (if it's not already):

```bash
# On macOS and most Linux systems:
source venv/bin/activate

# On Windows (Command Prompt):
venv\Scripts\activate.bat

# On Windows (PowerShell):
venv\Scripts\Activate.ps1
```

2. Navigate to the `src` directory in your terminal:

```bash
cd src
```

3. Run the Flask application:

```bash
python app.py
```

   Note: When the virtual environment is activated, you can use `python` without version suffixes, regardless of your operating system.

4. Open your web browser and go to:

```
http://localhost:5000
```

5. If you encounter any issues:
   - Make sure your virtual environment is activated (your command prompt should show `(venv)` at the beginning)
   - Ensure all required packages are installed correctly within the virtual environment
   - Check that you're in the correct directory (the `src` folder)
   - Ensure no other application is using port 5000
   - If you see an "externally-managed-environment" error, it means you're trying to install packages globally instead of in a virtual environment

## How It Works

The application scrapes Goodreads to-read lists for multiple users and finds books that appear across multiple lists. The data is displayed in a user-friendly web interface that allows for filtering and sorting.

- The backend is written in Python using Flask
- The frontend uses HTML, CSS, and JavaScript
- Data is fetched asynchronously using JavaScript fetch API

## Customization

To add or modify users, edit the `user_data` dictionary in `bookclub.py`:

```python
user_data = {
    "Username": "GoodreadsUserID",
    # Add more users here
}
```

## Note

This application is for educational purposes only. Please be respectful of Goodreads' terms of service and rate limits when using this tool.

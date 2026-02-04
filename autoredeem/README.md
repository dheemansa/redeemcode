# AutoRedeem Bot

A high-performance, Selenium-based Python script to automatically redeem Google Play codes.

## Prerequisites

- **Python 3.7+**
- **Google Chrome** installed.
- **ChromeDriver** (Managed automatically by Selenium or installed manually).

## Installation

1.  Create a virtual environment (optional but recommended):

    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

2.  Install dependencies:
    ```bash
    pip install selenium
    ```

## Using as a Python Module

You can easily integrate `AutoRedeemer` into your own Python projects.

### Example Code

```python
from autoredeem import AutoRedeemer
import time

def main():
    # 1. Initialize the bot
    # This automatically opens the browser and logs in (warm start)
    # headless=True is recommended for background processing
    bot = AutoRedeemer(dry_run=False, headless=True)

    print("Bot is ready! Waiting for codes...")

        # 2. Redeem a code
        code = "X9Q2-Z7LM-4K8A-PW3R"
        result = bot.redeem(code)

        print(f"Redemption Result: {result}")

        # 3. Redeem another code without restarting browser (Fast!)
        # result2 = bot.redeem("ANOTHER-CODE")
if __name__ == "__main__":
    main()
```

### Return Values

The `.redeem(code)` method returns one of the following strings:

- `"SUCCESS"`: Code was valid and redeemed.
- `"INVALID"`: Code was incorrect or expired.
- `"ALREADY_USED"`: Code has already been redeemed.
- `"LOGIN_REQ"`: Google asked for password verification (rare with cookies) or failed to login.
- `"ERROR"`: General error occurred.

## Using as a Standalone Tool

You can also run it directly from the terminal for quick testing.

### 1. First Run (Login)

On the first run, the script will detect missing cookies and automatically open a visible Chrome window.

1.  Run the script:
    ```bash
    python3 autoredeem.py <YOUR_CODE>
    ```
2.  Log in to your Google Account in the browser window that opens.
3.  Press **ENTER** in the terminal once logged in.
4.  The script will save your cookies to `google_cookies.pkl` and proceed.

### 2. Standard Usage

Once logged in, run the script with a code to redeem it instantly in headless mode:

```bash
python3 autoredeem.py X9Q2-Z7LM-4K8A-PW3R
```

## Configuration

You can modify the default settings in `autoredeem.py` inside the `__init__` method or by passing arguments:

- `dry_run=True`: **Safe Mode.** It injects the code and verifies that the "Confirm" button is detected correctly, but
  **does not click it**. Useful for testing if the bot can "see" the UI without actually redeeming the code.
- `headless=False`: Runs the browser visibly (good for debugging).
- `timeout=20`: Sets the maximum time (in seconds) to wait for the "Confirm" button to appear. Increase this if your
  internet is slow.

## Troubleshooting

- **Login / Session Issues:** If the bot fails to stay logged in or asks for login repeatedly, the cookies might be
  corrupted or expired.
    - **Fix:** Delete the `google_cookies.pkl` file and run the script again to generate fresh cookies.

- **"Cookies missing" loop:** If the above doesn't work, delete both `google_cookies.pkl` and the `chrome_profile/`
  folder to reset completely.

- **Crashes on Linux:** Ensure you have `--disable-gpu` and `--disable-dev-shm-usage` flags enabled (already set in
  code).

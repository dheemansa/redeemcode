import time
import pickle
import os
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

# only for termux
from selenium.webdriver.chrome.service import Service


class AutoRedeemer:
    """
    A class to automate the redemption of Google Play codes using Selenium.

    Attributes:
        dry_run (bool): If True, simulates redemption without clicking the final confirm button.
        headless (bool): If True, runs the browser in the background.
        timeout (int): Maximum time (seconds) to wait for the Confirm button.
    """

    def __init__(
        self,
        dry_run: bool = False,
        headless: bool = False,
        timeout: int = 20,
        profile_path: str = "./chrome_profile",
    ):
        """
        Initializes the AutoRedeemer bot.

        Args:
            dry_run (bool): Enable safe testing mode (no final click). Defaults to False.
            headless (bool): Run Chrome in headless mode. Defaults to False.
            timeout (int): Wait timeout for UI elements. Defaults to 20.
            profile_path (str): Path to the Chrome user data directory. Defaults to "./chrome_profile".
        """
        self.cookie_file = "google_cookies.pkl"
        self.dry_run = dry_run
        self.headless = headless
        self.timeout = timeout
        self.profile_path = profile_path

        # Initialize Driver Immediately (Warm Up)
        self.driver = self._get_driver(self.headless)

        # Load Cookies / Handle Login Immediately
        if not self._load_cookies():
            if self.headless:
                print("Cookies missing. Switching to visible mode for login...")
                self.driver.quit()
                self.driver = self._get_driver(headless=False)

            self._manual_login()
            # Reload to ensure we are in a good state
            self._load_cookies()

    def __del__(self):
        """
        Cleanup: Ensure the driver is closed when the object is destroyed.
        """
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass

    def _get_driver(self, headless: bool) -> webdriver.Chrome:
        """
        Configures and returns a Selenium WebDriver instance with optimizations.

        Args:
            headless (bool): Whether to run in headless mode.

        Returns:
            webdriver.Chrome: The configured Chrome driver.
        """
        options = webdriver.ChromeOptions()

        # only for termux
        # options.binary_location = "/data/data/com.termux/files/bin/chromium-browser"
        if headless:
            options.add_argument("--headless=new")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("--no-sandbox")
        options.add_argument("--log-level=3")
        options.add_argument(f"--user-data-dir={self.profile_path}")

        # Optimizations
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_argument("--window-size=1920,1080")
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        options.page_load_strategy = "eager"

        # Block images for faster loading
        prefs = {"profile.managed_default_content_settings.images": 2}
        options.add_experimental_option("prefs", prefs)

        # only for termux
        # service = Service(executable_path="/data/data/com.termux/files/usr/bin/chromedriver")
        # return webdriver.Chrome(options=options,service=service)
        return webdriver.Chrome(options=options)

    def _load_cookies(self) -> bool:
        """
        Attempts to load session cookies from a pickle file.

        Returns:
            bool: True if cookies were loaded and added successfully, False otherwise.
        """
        if os.path.exists(self.cookie_file):
            try:
                with open(self.cookie_file, "rb") as f:
                    cookies = pickle.load(f)
                    try:
                        self.driver.get("https://play.google.com")
                    except Exception:
                        pass
                    for cookie in cookies:
                        try:
                            self.driver.add_cookie(cookie)
                        except Exception:
                            pass
                    return True
            except Exception as e:
                print(f"Cookie load failed: {e}")
                return False
        return False

    def redeem_code(self, code: str) -> str:
        """
        Main logic to redeem a Google Play code.

        Args:
            code (str): The alphanumeric code to redeem.

        Returns:
            str: Result status (SUCCESS, INVALID, ALREADY_USED, etc.)
        """
        print(f"\n--- Processing Code: {code} ---")

        # 1. URL Injection
        url = f"https://play.google.com/redeem?code={code}"
        try:
            self.driver.get(url)
        except Exception:
            pass

        wait = WebDriverWait(self.driver, self.timeout)

        # 3. Check for Confirm Button (The Real Test)
        print("Waiting for Confirm button (Priority)...")

        try:
            # Priority: Wait explicitly for the Confirm button to be clickable
            confirm_btn = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(text(), 'Confirm')]")
                )
            )
            print(">>> CONFIRM BUTTON FOUND! Code is VALID.")

            if self.dry_run:
                print("DRY RUN: Skipping click.")
                return "SUCCESS (Dry Run)"

            print("Redeeming...")
            confirm_btn.click()
            time.sleep(3)
            return "SUCCESS"

        except TimeoutException:
            print("Confirm button not found within time limit.")

        # 4. If Confirm timed out, check if it was because the code is Invalid
        try:
            invalid_elements = self.driver.find_elements(
                By.XPATH, '//*[contains(text(), "That code didn\'t work")]'
            )
            if invalid_elements:
                print(">>> Invalid code message detected.")
                return "INVALID"
        except Exception:
            pass

        return self._get_status_text()

    def _get_status_text(self) -> str:
        """
        Scans the page body text to determine the final status if specific buttons are missing.

        Returns:
            str: The inferred status code.
        """
        try:
            text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
            if "successfully redeemed" in text or "added to your account" in text:
                return "SUCCESS"
            if "already redeemed" in text or "already been used" in text:
                return "ALREADY_USED"
            if "code didn't work" in text or "invalid code" in text:
                return "INVALID"
            if "verify it's you" in text or "you must sign in" in text:
                return "LOGIN_REQ"
            return "UNKNOWN_ERROR"
        except Exception:
            return "ERROR"

    def _manual_login(self):
        """
        Opens a visible browser window to allow the user to log in manually.
        Saves the cookies after the user presses Enter.
        """
        print("\n=== MANUAL LOGIN REQUIRED ===")
        print("Opening browser for login...")
        self.driver.get("https://play.google.com/redeem")
        input(
            "Please log in to your Google account in the browser.\nOnce logged in, press ENTER here to save cookies and continue..."
        )

        # Save cookies
        with open(self.cookie_file, "wb") as f:
            pickle.dump(self.driver.get_cookies(), f)
        print("✓ Cookies saved successfully.\n")

    def redeem(self, code: str) -> str:
        """
        Public entry point to execute the redemption process.

        Args:
            code (str): The code to redeem.

        Returns:
            str: The final status code (SUCCESS, INVALID, etc).
        """
        result = self.redeem_code(code)
        print(f"FINAL RESULT: {result}")
        # Driver is cleaned up by __del__ or manually
        if self.driver:
            self.driver.quit()
            self.driver = None
        return result


if __name__ == "__main__":
    if len(sys.argv) > 1:
        code_to_check = sys.argv[1]
    else:
        code_to_check = input("Enter code to redeem: ")

    # Auto-Redeem Optimized Configuration
    # dry_run=False (Real Redemption)
    # headless=True (Background Run)
    bot = AutoRedeemer(dry_run=False, headless=True, timeout=30)

    # Warm-up time (Browser is already open at this point)
    # This sleep allows the browser to settle if needed, but since we are "eager",
    # we can probably reduce this or remove it. Leaving 2s for stability.
    time.sleep(2)

    start = time.perf_counter()
    bot.redeem(code_to_check)
    end = time.perf_counter()
    print(f"Total Time: {end - start:.4f}s")

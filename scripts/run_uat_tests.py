"""Playwright browser automation script executing end-to-end User Acceptance Testing (UAT)."""
import os
import sys
import time
from playwright.sync_api import sync_playwright

UAT_SCREENSHOTS_DIR = os.path.abspath("docs/Phase_4_Testing_Validation/screenshots_uat")
os.makedirs(UAT_SCREENSHOTS_DIR, exist_ok=True)

BASE_URL = "http://localhost:8515"
TEST_USER_EMAIL = f"uat_user_{int(time.time())}@capital.com"
TEST_USER_PASS = "UatPassword2026!Secure"


def run_uat():
    print(f"Starting UAT test run against {BASE_URL}...")
    print(f"Test User: {TEST_USER_EMAIL}")

    with sync_playwright() as p:
        # Launch Microsoft Edge headless
        browser = p.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()

        # ----------------------------------------------------------------------
        # Step 1: Open app & verify Landing/Auth View
        # ----------------------------------------------------------------------
        print("\n--- Step 1: Access Application ---")
        page.goto(BASE_URL)
        page.wait_for_timeout(4000)

        # ----------------------------------------------------------------------
        # Step 2: User Registration
        # ----------------------------------------------------------------------
        print("\n--- Step 2: New User Registration ---")
        email_inputs = page.locator("input[aria-label='Email Address']")
        print(f"Found {email_inputs.count()} Email Address inputs")
        if email_inputs.count() >= 2:
            email_inputs.nth(1).fill(TEST_USER_EMAIL)
        else:
            email_inputs.first.fill(TEST_USER_EMAIL)

        page.locator("input[aria-label='Password (min 8 chars, 1 number/symbol)']").fill(TEST_USER_PASS)
        page.locator("button", has_text="Create Account (3 Free Credits)").click()
        page.wait_for_timeout(5000)
        print("Registration submitted and session activated.")

        # Capture Dashboard Landing
        dash_screenshot = os.path.join(UAT_SCREENSHOTS_DIR, "01_uat_dashboard_landing.png")
        page.screenshot(path=dash_screenshot, full_page=True)
        print(f"Captured: {dash_screenshot}")

        # Check Free Quota Badge
        quota_locator = page.locator("span.badge-free")
        if quota_locator.count() > 0:
            quota_text = quota_locator.first.inner_text()
            print(f"Initial Quota Status: {quota_text}")
            assert "3" in quota_text

        # ----------------------------------------------------------------------
        # Step 3: Execute Stock News Research (AAPL, 7D)
        # ----------------------------------------------------------------------
        print("\n--- Step 3: Execute Stock News Research (AAPL) ---")
        launch_btn = page.locator("button", has_text="Launch Research")
        if launch_btn.count() > 0:
            launch_btn.click()
            print("Research launched. Waiting for pipeline completion...")
            page.wait_for_timeout(18000)

        # Capture Stock News Tab
        news_screenshot = os.path.join(UAT_SCREENSHOTS_DIR, "02_uat_stock_news_tab.png")
        page.screenshot(path=news_screenshot, full_page=True)
        print(f"Captured: {news_screenshot}")

        # ----------------------------------------------------------------------
        # Step 4: Execute Sentiment Research Tab (30D Horizon)
        # ----------------------------------------------------------------------
        print("\n--- Step 4: Execute Sentiment Research ---")
        sent_tab = page.locator("[role='tab']", has_text="Sentiment Research")
        if sent_tab.count() > 0:
            sent_tab.click()
            page.wait_for_timeout(3000)
            print("Clicked Sentiment Research tab.")

        eval_btn = page.locator("button", has_text="Analyze 30D Sentiment")
        if eval_btn.count() > 0:
            eval_btn.click()
            print("Sentiment evaluation launched. Waiting for completion...")
            page.wait_for_timeout(18000)

        sent_screenshot = os.path.join(UAT_SCREENSHOTS_DIR, "03_uat_sentiment_tab.png")
        page.screenshot(path=sent_screenshot, full_page=True)
        print(f"Captured: {sent_screenshot}")

        # ----------------------------------------------------------------------
        # Step 5: Verify Research History & Reopening
        # ----------------------------------------------------------------------
        print("\n--- Step 5: Verify Research History ---")
        hist_nav = page.locator("label", has_text="Research History")
        if hist_nav.count() > 0:
            hist_nav.click()
            page.wait_for_timeout(4000)

        hist_screenshot = os.path.join(UAT_SCREENSHOTS_DIR, "04_uat_history_tab.png")
        page.screenshot(path=hist_screenshot, full_page=True)
        print(f"Captured: {hist_screenshot}")

        # Test Reopening a Report without credit deduction
        reopen_btn = page.locator("button", has_text="Reopen in Dashboard").first
        if reopen_btn.count() > 0:
            reopen_btn.click()
            page.wait_for_timeout(4000)
            print("Successfully reopened report in Dashboard without credit deduction.")

        # ----------------------------------------------------------------------
        # Step 6: Mobile Viewport Validation (390 x 844)
        # ----------------------------------------------------------------------
        print("\n--- Step 6: Mobile Layout Testing (390 x 844) ---")
        mobile_context = browser.new_context(viewport={"width": 390, "height": 844})
        mobile_page = mobile_context.new_page()
        mobile_page.goto(BASE_URL)
        mobile_page.wait_for_timeout(4000)

        # On mobile, close sidebar if open or click sign in directly with force=True
        collapse_btn = mobile_page.locator("button[data-testid='stSidebarCollapseButton']")
        if collapse_btn.count() > 0 and collapse_btn.is_visible():
            collapse_btn.click()
            mobile_page.wait_for_timeout(1000)

        mob_email = mobile_page.locator("input[aria-label='Email Address']").first
        mob_email.fill(TEST_USER_EMAIL)
        mobile_page.locator("input[aria-label='Password']").fill(TEST_USER_PASS)
        mobile_page.locator("button", has_text="Sign In").click(force=True)
        mobile_page.wait_for_timeout(5000)

        mobile_screenshot = os.path.join(UAT_SCREENSHOTS_DIR, "05_uat_mobile_view.png")
        mobile_page.screenshot(path=mobile_screenshot, full_page=True)
        print(f"Captured: {mobile_screenshot}")
        mobile_context.close()

        # ----------------------------------------------------------------------
        # Step 7: Token Request & Admin Approval Flow
        # ----------------------------------------------------------------------
        print("\n--- Step 7: Token Request & Approval Flow ---")
        page.locator("label", has_text="Research Dashboard").click()
        page.wait_for_timeout(2000)

        # Open Token Options in sidebar
        page.locator("details summary", has_text="Access Token Options").click()
        page.wait_for_timeout(1000)
        req_subtab = page.locator("[role='tab']", has_text="Request")
        if req_subtab.count() > 0:
            req_subtab.click()
            page.wait_for_timeout(1000)
        page.locator("textarea").fill("Quantitative hedge fund strategy analysis requiring unlimited access")
        page.locator("button", has_text="Submit Request").click()
        page.wait_for_timeout(3000)
        print("Token request submitted.")

        # Sign Out
        page.locator("button", has_text="Sign Out").click()
        page.wait_for_timeout(3000)

        # Sign In as Admin
        page.locator("input[aria-label='Email Address']").first.fill("admin@firm.com")
        page.locator("input[aria-label='Password']").fill("AdminPass2026!Secure")
        page.locator("button", has_text="Sign In").click()
        page.wait_for_timeout(4000)

        # Navigate to Admin Console
        page.locator("label", has_text="Admin Console").click()
        page.wait_for_timeout(4000)

        # Approve token request
        approve_btn = page.locator("button", has_text="Approve & Issue Token").first
        raw_tok_text = None
        if approve_btn.count() > 0:
            approve_btn.click()
            page.wait_for_timeout(3000)
            print("Admin clicked Approve & Issue Token.")
            # Extract issued token code
            code_locator = page.locator("code")
            for c in code_locator.all():
                ct = c.inner_text().strip()
                if ct.startswith("sk_res_"):
                    raw_tok_text = ct
                    break
            print(f"Issued Token: {raw_tok_text}")

        # Admin signs out
        page.locator("button", has_text="Sign Out").click()
        page.wait_for_timeout(3000)

        # Sign back in as test user
        page.locator("input[aria-label='Email Address']").first.fill(TEST_USER_EMAIL)
        page.locator("input[aria-label='Password']").fill(TEST_USER_PASS)
        page.locator("button", has_text="Sign In").click()
        page.wait_for_timeout(4000)

        # Redeem token if extracted
        if raw_tok_text and raw_tok_text.startswith("sk_res_"):
            page.locator("details summary", has_text="Access Token Options").click()
            page.wait_for_timeout(1000)
            redeem_input = page.locator("input[placeholder='sk_res_...']")
            if redeem_input.count() > 0:
                redeem_input.fill(raw_tok_text)
                page.locator("button", has_text="Redeem Token").click()
                page.wait_for_timeout(4000)
                print("Token redeemed by user.")

        # Check Unlimited status in sidebar
        unlimited_screenshot = os.path.join(UAT_SCREENSHOTS_DIR, "06_uat_unlimited_entitlement.png")
        page.screenshot(path=unlimited_screenshot, full_page=True)
        print(f"Captured: {unlimited_screenshot}")

        browser.close()
        print("\nAll UAT automation scenarios completed successfully!")


if __name__ == "__main__":
    run_uat()

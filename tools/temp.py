from playwright.sync_api import sync_playwright


url = "https://www.netacad.com/learning-collections/python"

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=False
    )

    page = browser.new_page()

    print("Opening:", url)

    response = page.goto(
        url,
        wait_until="domcontentloaded",
        timeout=30000,
    )

    print("Status:", response.status if response else None)
    print("URL:", page.url)
    print("Title:", page.title())

    page.wait_for_timeout(10000)

    print("\nBODY TEXT:")
    print(page.locator("body").inner_text()[:5000])

    page.screenshot(
        path="netacad_debug.png",
        full_page=True
    )

    page.content()

    with open(
        "netacad_debug.html",
        "w",
        encoding="utf-8"
    ) as f:
        f.write(page.content())

    input("\nPress Enter to close...")

    browser.close()

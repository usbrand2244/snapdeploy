# app.py
import asyncio
import os
from flask import Flask, jsonify
from playwright.async_api import async_playwright

app = Flask(__name__)

# Try a working VidSrc domain. vidsrc.to often has issues.
# Other known domains: vidsrc.net, vidsrc.xyz, vidsrc.in, vidsrc.pm
VIDSRC_MOVIE_URL = "https://vidsrc.to/embed/movie/{}"


async def extract_m3u8(imdb_id: str):
    found_urls = []
    embed_url = VIDSRC_MOVIE_URL.format(imdb_id)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled", # Helps avoid detection
            ]
        )
        
        # Create a context that looks more like a real browser
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
        )
        
        page = await context.new_page()

        # --- FIX 1: Block unnecessary resources to speed up loading ---
        # This prevents images, fonts, and media from slowing down the page.
        await page.route("**/*", lambda route: route.abort() 
                         if route.request.resource_type in ["image", "font", "media"] 
                         else route.continue_())

        # Listener to capture the .m3u8 request
        async def handle_response(response):
            url = response.url
            if ".m3u8" in url and url not in found_urls:
                found_urls.append(url)

        page.on("response", handle_response)

        try:
            # --- FIX 2: Use 'domcontentloaded' instead of 'networkidle' ---
            # This waits only for the HTML to be parsed, not for all network activity to stop.
            await page.goto(embed_url, wait_until="domcontentloaded", timeout=30000)
            
            # --- FIX 3: Give the player extra time to fire the m3u8 request ---
            # Even after DOM load, the player's JavaScript needs time to run.
            await asyncio.sleep(8)  # Wait 8 seconds for the stream request

        except Exception as e:
            await browser.close()
            return {"success": False, "error": str(e), "urls": []}

        await browser.close()

    if found_urls:
        return {"success": True, "urls": found_urls, "embed_url": embed_url}
    else:
        return {
            "success": False,
            "error": "No .m3u8 URL found. The player may be protected, the domain is blocked, or the ID is invalid.",
            "embed_url": embed_url,
            "urls": [],
        }


# Flask routes remain the same...
@app.route("/stream/<imdb_id>", methods=["GET"])
def stream(imdb_id):
    result = asyncio.run(extract_m3u8(imdb_id))
    return jsonify(result)

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "service": "IMDb to M3U8 Resolver",
        "usage": "GET /stream/<imdb_id>",
        "example": "/stream/tt0111161"
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)

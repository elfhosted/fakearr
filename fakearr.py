import os
import requests
import json
import logging
import xml.etree.ElementTree as ET
from flask import Flask, request, Response, send_file


logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

app = Flask(__name__)

# Stremio Addon Config
STREMIO_BASE_URL = os.getenv("EASYNEWSPLUS_URL", "http://elfhosted-internal.easynewsplus")
USERNAME = os.getenv("EASYNEWS_USERNAME", "default_user")
PASSWORD = os.getenv("EASYNEWS_PASSWORD", "default_pass")
FAKEARR_BASE_URL = os.getenv('FAKEARR_BASE_URL', 'http://debridav:5001')

FAKE_NZB_DIR = "/tmp/nzb_files"
os.makedirs(FAKE_NZB_DIR, exist_ok=True)

# Helper function to generate XML response
def xml_response(root_element):
    xml_str = ET.tostring(root_element, encoding="utf-8", xml_declaration=True)
    return Response(xml_str, mimetype="application/xml")

# Function to query Stremio addon
def query_stremio(imdbid=None, season=None, episode=None):
    auth_payload = json.dumps({
        "username": USERNAME,
        "password": PASSWORD,
        "sort1": "Size", "sort1Direction": "Descending",
        "sort2": "Relevance", "sort2Direction": "Descending",
        "sort3": "Date & Time", "sort3Direction": "Descending"
    })

    if season and episode:
        url = f"{STREMIO_BASE_URL}/{auth_payload}/stream/series/{imdbid or 'tt9288030'}:{season}:{episode}.json"
    else:
        url = f"{STREMIO_BASE_URL}/{auth_payload}/stream/movie/{imdbid or 'tt0137523'}.json"

    # Query the Stremio API
    logging.debug(f"Querying Stremio with URL: {url}")
    response = requests.get(url)
    if response.status_code != 200:
        logging.error(f"Stremio request failed with status {response.status_code}: {response.text}")
        return []

    try:
        json_response = response.json()
        return json_response.get("streams", [])
    except json.JSONDecodeError:
        logging.error("Failed to parse JSON response from Stremio.")
        return []


    return response.json().get("streams", [])

@app.route("/api", methods=["GET"])
def newznab_api():
    mode = request.args.get("t")

    # # Check for `q` in the query parameters and return null if found
    # if request.args.get("q"):
    #     return "null"

    # Redirect /api?t=movie and /api?t=tvsearch to /api?t=search
    if mode == "movie" or mode == "tv":
        mode = "search"

    # --- CAPS RESPONSE ---
    if mode == "caps":
        root = ET.Element("caps")
        
        # Server info
        server = ET.SubElement(root, "server", 
                               appversion="0.8.21.0", 
                               version="0.1", 
                               title="ElfEasyNews", 
                               strapline="ElfEasyNews Indexer", 
                               email="support@elfeasynews.com", 
                               meta="elf, easynews, indexer", 
                               url="https://elfeasynews.com", 
                               image="https://elfeasynews.com/logo.png")
        
        # Limits
        limits = ET.SubElement(root, "limits", max="100", default="50")
        
        # Registration info
        registration = ET.SubElement(root, "registration", available="yes", open="no")
        
        # Searching capabilities
        searching = ET.SubElement(root, "searching")
        ET.SubElement(searching, "search", available="yes", supportedParams="q")
        ET.SubElement(searching, "tv-search", available="yes", supportedParams="q, imdbid, season, ep, tvdbid, traktid, rid, tvmazeid")
        ET.SubElement(searching, "movie-search", available="yes", supportedParams="q, imdbid")
        ET.SubElement(searching, "audio-search", available="no", supportedParams="")
        
        # Categories
        categories = ET.SubElement(root, "categories")
        categories_data = [
            {"id": "2000", "name": "Movies"},
            {"id": "3000", "name": "Audio", "subcats": [
                {"id": "3030", "name": "Audiobook"}, {"id": "3010", "name": "MP3"}]},
            {"id": "5000", "name": "TV"}]

        for category in categories_data:
            category_element = ET.SubElement(categories, "category", id=category["id"], name=category["name"])
            for subcat in category["subcats"]:
                ET.SubElement(category_element, "subcat", id=subcat["id"], name=subcat["name"])

        return xml_response(root)

    # --- SEARCH RESPONSE ---
    elif mode == "search":
        imdbid = request.args.get("imdbid")
        season = request.args.get("season")
        episode = request.args.get("ep")

        # Check if imdbid is provided and if it starts with 'tt'. If not, add 'tt' at the beginning.
        if imdbid and not imdbid.startswith("tt"):
            imdbid = "tt" + imdbid        

        # If no search terms are provided, return predefined fake results (TV and Movie)
        if not imdbid and not season and not episode:
            results = [
                # Fake TV Episode
                {
                    "name": "Fake TV Show",
                    "behaviorHints": {"fileName": "Fake TV Show", "videoSize": 500000000},
                    "description": "Fake TV Show Season 1 Episode 1",
                    "url": "http://fakeurl.com/fake-tv-show-episode1.mp4"
                },
                # Fake Movie
                {
                    "name": "Fake Movie",
                    "behaviorHints": {"fileName": "Fake Movie", "videoSize": 1500000000},
                    "description": "Fake Movie Description",
                    "url": "http://fakeurl.com/fake-movie.mp4"
                }
            ]
        else:
            # Query the Stremio API if search terms are provided
            results = query_stremio(imdbid, season, episode)

        # Count the number of results
        result_count = len(results)

        # Log the result count
        logging.info(f"Results found: {result_count}")


        rss = ET.Element("rss", attrib={
            "version": "2.0", 
            "xmlns:atom": "http://www.w3.org/2005/Atom", 
            "xmlns:newznab": "http://www.newznab.com/DTD/2010/feeds/attributes/", 
            "encoding": "utf-8"
        })
        channel = ET.SubElement(rss, "channel")

        ET.SubElement(channel, "title").text = "ElfEasyNews Results"
        ET.SubElement(channel, "description").text = "A custom indexer for Stremio-based searches."
        ET.SubElement(channel, "link").text = FAKEARR_BASE_URL
        ET.SubElement(channel, "language").text = "en-us"


        for result in results:
            title = result.get("behaviorHints", {}).get("fileName") or result.get("name", "Unknown Title")
            size = str(result.get("behaviorHints", {}).get("videoSize", 104857600))
            quality = result.get("name", "Unknown Quality")
            nzb_url = f"{FAKEARR_BASE_URL}/fake_nzb/{title}.nzb"

            item = ET.SubElement(channel, "item")
            ET.SubElement(item, "title").text = title
            ET.SubElement(item, "description").text = title
            ET.SubElement(item, "link").text = nzb_url

            guid = ET.SubElement(item, "guid")
            guid.text = nzb_url
            guid.set("isPermaLink", "true")

            if title == "Fake TV Show" or season:
                category_text = "TV"   
                category_id = "5000"
            else:
                category_id = "2000"
                category_text = "Movies"            
                
            ET.SubElement(item, "pubDate").text = "Mon, 25 Mar 2024 12:00:00 GMT"
            
            # Add both formats for category
            ET.SubElement(item, "category").text = category_text  # Standard format
            ET.SubElement(item, "newznab:attr", {"name": "category", "value": category_id})  # Prowlarr format

            enclosure = ET.SubElement(item, "enclosure")
            enclosure.set("url", nzb_url)
            enclosure.set("length", size)
            enclosure.set("type", "application/x-nzb")

            attrs = [
                ("size", size),
                ("grabs", "0"),
                ("usenetdate", "2025-03-25 12:00:00"),
                ("poster", "user@example.com"),
                ("group", "alt.binaries.example"),
                ("quality", quality),
            ]

            for attr_name, attr_value in attrs:
                ET.SubElement(item, "newznab:attr", {"name": attr_name, "value": attr_value})

        return xml_response(rss)

    return "Invalid request", 400


@app.route("/fake_nzb/<filename>.nzb", methods=["GET"])
def generate_fake_nzb(filename):
    """Dynamically generate a fake NZB file."""
    fake_nzb_path = os.path.join(FAKE_NZB_DIR, f"{filename}.nzb")

    if not os.path.exists(fake_nzb_path):
        with open(fake_nzb_path, "w") as f:
            f.write(f"""<?xml version="1.0" encoding="utf-8"?>
<nzb xmlns="http://www.newzbin.com/DTD/2003/nzb">
    <file poster="user@example.com" date="1711584000" subject="{filename}">
        <groups><group>alt.binaries.example</group></groups>
        <segments>
            <segment bytes="104857600" number="1">FAKE_SEGMENT_ID</segment>
        </segments>
    </file>
</nzb>""")

    return send_file(fake_nzb_path, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)

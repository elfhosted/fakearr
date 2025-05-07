import os
import requests
import json
import logging
import urllib.parse
import xml.etree.ElementTree as ET
from flask import Flask, request, Response, send_file
from datetime import datetime

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

app = Flask(__name__)

# Configuration from environment variables
STREMIO_BASE_URL = os.getenv("EASYNEWS_ADDON_URL", "http://elfhosted-internal.easynewsplus")
USERNAME = os.getenv("EASYNEWS_USERNAME", "default_user")
PASSWORD = os.getenv("EASYNEWS_PASSWORD", "default_pass")
FAKEARR_BASE_URL = os.getenv("FAKEARR_BASE_URL", "http://debridav:5001")
EASYNEWS_VERSION = os.getenv("EASYNEWS_VERSION", "plus").lower()

FAKE_NZB_DIR = "/tmp/nzb_files"
os.makedirs(FAKE_NZB_DIR, exist_ok=True)

def xml_response(root_element):
    xml_str = ET.tostring(root_element, encoding="utf-8", xml_declaration=True)
    return Response(xml_str, mimetype="application/xml")

def query_stremio(imdbid=None, season=None, episode=None):
    if not imdbid:
        return []

    if EASYNEWS_VERSION == "plus":
        auth_payload = {
            "username": USERNAME,
            "password": PASSWORD,
            "sort1": os.getenv("EASYNEWS_SORT1", "Size"),
            "sort1Direction": os.getenv("EASYNEWS_SORT1_DIR", "Descending"),
            "sort2": os.getenv("EASYNEWS_SORT2", "Relevance"),
            "sort2Direction": os.getenv("EASYNEWS_SORT2_DIR", "Descending"),
            "sort3": os.getenv("EASYNEWS_SORT3", "Date & Time"),
            "sort3Direction": os.getenv("EASYNEWS_SORT3_DIR", "Descending")
        }
    elif EASYNEWS_VERSION == "plusplus":
        auth_payload = {
            "uiLanguage": os.getenv("EASYNEWS_UI_LANGUAGE", "eng"),
            "username": USERNAME,
            "password": PASSWORD,
            "strictTitleMatching": os.getenv("EASYNEWS_STRICT_TITLE_MATCHING", "on"),
            "preferredLanguage": os.getenv("EASYNEWS_PREFERRED_LANGUAGE", ""),
            "sortingPreference": os.getenv("EASYNEWS_SORTING_PREFERENCE", "quality_first"),
            "showQualities": os.getenv("EASYNEWS_SHOW_QUALITIES", "4k,1080p,720p,480p"),
            "maxResultsPerQuality": os.getenv("EASYNEWS_MAX_RESULTS_PER_QUALITY", ""),
            "maxFileSize": os.getenv("EASYNEWS_MAX_FILE_SIZE", "")
        }
    else:
        logging.error("Invalid EASYNEWS_VERSION setting. Must be 'plus' or 'plusplus'.")
        return []

    encoded_auth = urllib.parse.quote(json.dumps(auth_payload))

    if season and episode:
        url = f"{STREMIO_BASE_URL}/{encoded_auth}/stream/series/{imdbid}:{season}:{episode}.json"
    else:
        url = f"{STREMIO_BASE_URL}/{encoded_auth}/stream/movie/{imdbid}.json"

    logging.debug(f"Querying Stremio Addon ({EASYNEWS_VERSION}) with URL: {url}")

    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json().get("streams", [])
    except Exception as e:
        logging.error(f"Failed to query Stremio addon: {e}")
        return []

@app.route("/api", methods=["GET"])
def newznab_api():
    mode = request.args.get("t")

    if mode == "movie" or mode == "tvsearch":
        mode = "search"

    if mode == "caps":
        root = ET.Element("caps")
        ET.SubElement(root, "server", appversion="0.8.21.0", version="0.1", title="ElfEasyNews",
                      strapline="ElfEasyNews Indexer", email="support@elfeasynews.com",
                      meta="elf, easynews, indexer", url="https://elfeasynews.com",
                      image="https://elfeasynews.com/logo.png")
        ET.SubElement(root, "limits", max="100", default="50")
        ET.SubElement(root, "registration", available="yes", open="no")

        searching = ET.SubElement(root, "searching")
        ET.SubElement(searching, "search", available="yes", supportedParams="q")
        ET.SubElement(searching, "tv-search", available="yes",
                      supportedParams="q, imdbid, season, ep, tvdbid, traktid, rid, tvmazeid")
        ET.SubElement(searching, "movie-search", available="yes", supportedParams="q, imdbid")
        ET.SubElement(searching, "audio-search", available="no", supportedParams="")

        categories = ET.SubElement(root, "categories")
        categories_data = [
            {"id": "2000", "name": "Movies"},
            {"id": "3000", "name": "Audio", "subcats": [{"id": "3030", "name": "Audiobook"}, {"id": "3010", "name": "MP3"}]},
            {"id": "5000", "name": "TV"}
        ]
        for category in categories_data:
            category_element = ET.SubElement(categories, "category", id=category["id"], name=category["name"])
            if "subcats" in category:
                for subcat in category["subcats"]:
                    ET.SubElement(category_element, "subcat", id=subcat["id"], name=subcat["name"])
        return xml_response(root)

    elif mode == "search":
        imdbid = request.args.get("imdbid")
        season = request.args.get("season")
        episode = request.args.get("ep")
        q = request.args.get("q")

        if imdbid and not imdbid.startswith("tt"):
            imdbid = "tt" + imdbid

        if not imdbid and not season and not episode and not q:
            results = [
                {"name": "Fake TV Show", "behaviorHints": {"fileName": "Fake TV Show", "videoSize": 500000000},
                 "description": "Fake TV Show Season 1 Episode 1", "url": "http://fakeurl.com/fake-tv-show-episode1.mp4"},
                {"name": "Fake Movie", "behaviorHints": {"fileName": "Fake Movie", "videoSize": 1500000000},
                 "description": "Fake Movie Description", "url": "http://fakeurl.com/fake-movie.mp4"}
            ]
        else:
            results = query_stremio(imdbid, season, episode)

        logging.info(f"Results found: {len(results)}")

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
            if EASYNEWS_VERSION == "plus":
                title = result.get("behaviorHints", {}).get("fileName") or result.get("name", "Unknown Title")
                size = str(result.get("behaviorHints", {}).get("videoSize", 104857600))
                quality = result.get("name", "Unknown Quality")
                parsed_date = "2025-03-25 12:00:00"
                pub_date = "Tue, 25 Mar 2025 12:00:00 GMT"
                poster = "user@example.com"
                group = "alt.binaries.example"

            elif EASYNEWS_VERSION == "plusplus":
                title = result.get("behaviorHints", {}).get("filename") or result.get("name", "Unknown Title")
                size = str(result.get("_temp", {}).get("file", {}).get("rawSize", 104857600))
                quality = result.get("name", "Unknown Quality")
                raw_date = result.get("_temp", {}).get("file", {}).get("5", "")
                try:
                    dt_obj = datetime.strptime(raw_date, "%m-%d-%Y %H:%M:%S")
                    parsed_date = dt_obj.strftime("%Y-%m-%d %H:%M:%S")
                    pub_date = dt_obj.strftime("%a, %d %b %Y %H:%M:%S GMT")
                except Exception:
                    parsed_date = "2025-03-25 12:00:00"
                    pub_date = "Tue, 25 Mar 2025 12:00:00 GMT"
                poster = result.get("_temp", {}).get("file", {}).get("7", "user@example.com")
                group = result.get("_temp", {}).get("file", {}).get("9", "alt.binaries.example")

            nzb_url = f"{FAKEARR_BASE_URL}/fake_nzb/{title}.nzb"
            item = ET.SubElement(channel, "item")
            ET.SubElement(item, "title").text = title
            ET.SubElement(item, "description").text = title
            ET.SubElement(item, "link").text = nzb_url
            ET.SubElement(item, "guid", isPermaLink="true").text = nzb_url

            if title == "Fake TV Show" or season:
                category_text = "TV"
                category_id = "5000"
            else:
                category_text = "Movies"
                category_id = "2000"

            ET.SubElement(item, "pubDate").text = pub_date
            ET.SubElement(item, "category").text = category_text
            ET.SubElement(item, "newznab:attr", {"name": "category", "value": category_id})

            enclosure = ET.SubElement(item, "enclosure", url=nzb_url, length=size, type="application/x-nzb")

            attrs = [
                ("size", size),
                ("grabs", "0"),
                ("usenetdate", parsed_date),
                ("poster", poster),
                ("group", group),
                ("quality", quality),
            ]
            for attr_name, attr_value in attrs:
                ET.SubElement(item, "newznab:attr", {"name": attr_name, "value": attr_value})

        return xml_response(rss)

    return "Invalid request", 400

@app.route("/fake_nzb/<filename>.nzb", methods=["GET"])
def generate_fake_nzb(filename):
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

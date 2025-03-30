# FakeArr

FakeArr is a "workalike" implementation of Puks' original fake-torrent-server. It is designed to work seamlessly with [DebriDav](https://github.com/skjaere/DebriDav) and EasyNews, but instead of requiring a separate Prowlarr indexer definition, it functions as a NewzNab indexer.

FakeArr is used in the [ElfHosted EasyNews bundles](https://store.elfhosted.com/product-category/streaming-bundles/debrid-provider/easynews/), or as an [optional addon](https://store.elfhosted.com/product/debridav/) to any other ElfHosted stack, as demonstrated at https://www.youtube.com/watch?v=IkKQB61TL6I&t=7s

Grab a [7-day trial for $1](https://store.elfhosted.com/product/hobbit-plex-easynews-aars/) and see for yourself :)

## Features

- Acts as a NewzNab indexer for seamless integration.
- Compatible with DebriDav and EasyNews.
- Provides fake NZB files for testing and development purposes.

## Screenshots

Here's what Fakearr can enable in Radarr/Sonarr:

![](screenshots/fakearr-radarr-search.png)

![](screenshots/fakearr-sonarr-search.png)

And here's how to enable it in Prowlarr:

![](screenshots/fakearr-prowlarr.png)


## Environment Variables

To configure FakeArr, set the following environment variables:

| Variable            | Default Value                                   | Description                                   |
|---------------------|-------------------------------------------------|-----------------------------------------------|
| `EASYNEWSPLUS_URL`  | `http://elfhosted-internal.easynewsplus`        | Base URL for the Stremio addon.              |
| `EASYNEWS_USERNAME` | `default_user`                                  | Username for EasyNews authentication.        |
| `EASYNEWS_PASSWORD` | `default_pass`                                  | Password for EasyNews authentication.        |
| `FAKEARR_BASE_URL`  | `http://debridav:5001`                          | Base URL for FakeArr. Needs to be reachable from Aars                        |

## Getting Started

1. Clone the repository:
   ```bash
   git clone https://github.com/your-repo/fakearr.git
   cd fakearr
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run FakeArr!
   ```bash
   python fakearr.py
   ```
4. Access the API at http://localhost:5001/api

## Using Docker

```
docker run -d -p 5001:5001 \
  -e EASYNEWSPLUS_URL=https://easynewsplus.elfhosted.com \
  -e EASYNEWS_USERNAME=my_user \
  -e EASYNEWS_PASSWORD=my_pass \
  -e FAKEARR_BASE_URL=http://fakearr:5001 \
  --name fakearr ghcr.io/elfhosted/fakearr:rolling
  ```

## License

This project is licensed under the **Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)** license.

You are free to:
- **Share** — copy and redistribute the material in any medium or format.
- **Adapt** — remix, transform, and build upon the material.

**Under the following terms**:
- **Attribution** — You must give appropriate credit, provide a link to the license, and indicate if changes were made.
- **NonCommercial** — You may not use the material for commercial purposes.

For more details, see the full license text at [https://creativecommons.org/licenses/by-nc/4.0/](https://creativecommons.org/licenses/by-nc/4.0/).

# Acknowledgments

* Inspired by Puks The Pirate's original fake-torrent-server. See Puk's work at https://savvyguides.wiki/
* EasyNews search is made possible by https://github.com/sleeyax/stremio-easynews-addon

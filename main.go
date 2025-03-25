package main

import (
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"log"
	"net/http"
	"regexp"
	"time"
)

// generateFakeInfoHash creates a random 20-byte infohash
func generateFakeInfoHash() string {
	bytes := make([]byte, 20)
	_, err := rand.Read(bytes)
	if err != nil {
		log.Fatal("Failed to generate random infohash")
	}
	return hex.EncodeToString(bytes)
}

// generateFakeTorrent creates a fake torrent file content with a valid structure
func generateFakeTorrent(filename string) string {
	// Basic structure for the torrent
	infohash := generateFakeInfoHash()

	// The "info" dictionary inside the torrent file should be properly formatted
	torrentContent := fmt.Sprintf(`d8:announce13:fake-tracker4:infod4:name%d:%s6:lengthi123456e12:piece lengthi524288e6:pieces20:%se`, 
		len(filename), filename, infohash)

	// Return the content for the .torrent file
	return torrentContent
}

func generateFakeNZB(filename string) string {
	return fmt.Sprintf(`<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE nzb PUBLIC "-//newzBin//DTD NZB 1.1//EN" "http://www.newzbin.com/DTD/nzb/nzb-1.1.dtd">
<nzb>
  <file poster="fake@poster.com" date="%d" subject="%s.nzb">
    <groups>
      <group>alt.binaries.fake</group>
    </groups>
    <segments>
      <segment bytes="123456" number="1">fake-segment-1</segment>
    </segments>
  </file>
</nzb>`, 1234567890, filename)
}

// requestHandler processes both .torrent and .nzb requests
func requestHandler(w http.ResponseWriter, r *http.Request) {
	var re = regexp.MustCompile(`^/(.*)\.(torrent|nzb)$`)
	matches := re.FindStringSubmatch(r.URL.Path)
	if matches == nil || len(matches) < 3 {
		http.Error(w, "Invalid request", http.StatusBadRequest)
		return
	}

	filename := matches[1]
	switch matches[2] {
	case "torrent":
		torrentContent := generateFakeTorrent(filename)
		w.Header().Set("Content-Type", "application/x-bittorrent")
		w.Header().Set("Content-Disposition", fmt.Sprintf("attachment; filename=\"%s.torrent\"", filename))
		_, _ = w.Write([]byte(torrentContent))
	case "nzb":
		nzbContent := generateFakeNZB(filename)
		w.Header().Set("Content-Type", "application/x-nzb")
		w.Header().Set("Content-Disposition", fmt.Sprintf("attachment; filename=\"%s.nzb\"", filename))
		_, _ = w.Write([]byte(nzbContent))
	}
}

func main() {
	http.HandleFunc("/", requestHandler)
	port := 8000
	log.Printf("Starting fakearr on :%d", port)
	log.Fatal(http.ListenAndServe(fmt.Sprintf(":%d", port), nil))
}
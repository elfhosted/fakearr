package main

import (
	"bytes"
	"crypto/sha1"
	"fmt"
	"io"
	"log"
	"net/http"
	"regexp"
	"time"

	"github.com/anacrolix/torrent/bencode"
)

// generateFakeTorrent creates a mock torrent file for a given filename
func generateFakeTorrent(filename string) ([]byte, error) {
	// Calculate piece hashes
	pieceLength := 262144 // 256 KB
	totalSize := 1024 * 1024 * 1024 // 1 GB
	numPieces := (totalSize + pieceLength - 1) / pieceLength
	
	// Generate piece hashes
	pieces := make([]byte, numPieces*20)
	for i := 0; i < numPieces; i++ {
		// Create a deterministic but unique piece hash
		hash := sha1.New()
		hash.Write([]byte(fmt.Sprintf("piece_%d_%s", i, filename)))
		copy(pieces[i*20:], hash.Sum(nil))
	}

	// Construct torrent metadata
	torrentMetadata := map[string]interface{}{
		"info": map[string]interface{}{
			"name":         filename,
			"piece length": pieceLength,
			"pieces":       string(pieces),
			"length":       totalSize,
			"private":      0,
		},
		"announce":      "http://tracker.example.com/announce",
		"creation date": time.Now().Unix(),
		"created by":    "Fakearr",
		"info-hash":     generateInfoHash(pieces, filename),
	}

	// Encode the torrent metadata using bencode
	var buf bytes.Buffer
	encoder := bencode.NewEncoder(&buf)
	if err := encoder.Encode(torrentMetadata); err != nil {
		return nil, err
	}

	return buf.Bytes(), nil
}

// generateInfoHash creates a unique info hash based on pieces and filename
func generateInfoHash(pieces []byte, filename string) string {
	hash := sha1.New()
	hash.Write(pieces)
	hash.Write([]byte(filename))
	return string(hash.Sum(nil))
}

func main() {
	// Regex to match .torrent files
	torrентRegex := regexp.MustCompile(`^(.+)\.torrent$`)

	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		// Check if the request matches .torrent pattern
		matches := torrентRegex.FindStringSubmatch(r.URL.Path[1:])
		if matches == nil {
			http.NotFound(w, r)
			return
		}

		// Extract filename from the request
		originalFilename := matches[1]

		// Log the requested torrent filename
		fmt.Printf("Generating torrent for: %s\n", originalFilename)

		// Generate fake torrent
		torrentData, err := generateFakeTorrent(originalFilename)
		if err != nil {
			http.Error(w, "Failed to generate torrent", http.StatusInternalServerError)
			return
		}

		// Set appropriate headers
		w.Header().Set("Content-Type", "application/x-bittorrent")
		w.Header().Set("Content-Disposition", fmt.Sprintf("attachment; filename=\"%s.torrent\"", originalFilename))
		
		// Write torrent data
		_, err = io.Copy(w, bytes.NewReader(torrentData))
		if err != nil {
			log.Printf("Error writing torrent: %v", err)
		}
	})

	fmt.Println("Starting Fakearr on :8000")
	log.Fatal(http.ListenAndServe(":8000", nil))
}
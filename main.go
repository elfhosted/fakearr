package main

import (
	"bytes"
	"crypto/sha1"
	"encoding/xml"
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

// NZBFile represents the structure of an NZB file
type NZBFile struct {
	XMLName    xml.Name `xml:"nzb"`
	Xmlns      string   `xml:"xmlns,attr"`
	Head       NZBHead  `xml:"head"`
	File       []NZBFileSegment `xml:"file"`
}

type NZBHead struct {
	Meta []NZBMeta `xml:"meta"`
}

type NZBMeta struct {
	Type  string `xml:"type,attr"`
	Value string `xml:",chardata"`
}

type NZBFileSegment struct {
	Subject    string       `xml:"subject,attr"`
	Poster     string       `xml:"poster,attr"`
	Date       int64        `xml:"date,attr"`
	Groups     []string     `xml:"groups>group"`
	Segments   []NZBSegment `xml:"segments>segment"`
}

type NZBSegment struct {
	Number     int    `xml:"number,attr"`
	Size       int    `xml:"bytes,attr"`
	SegmentRef string `xml:",chardata"`
}

// generateFakeNZB creates a mock NZB file for a given filename
func generateFakeNZB(filename string) ([]byte, error) {
	// Current timestamp
	now := time.Now().Unix()

	// Create NZB structure
	nzb := NZBFile{
		Xmlns: "http://www.newzbin.com/DTD/2003/nzb",
		Head: NZBHead{
			Meta: []NZBMeta{
				{Type: "title", Value: filename},
				{Type: "category", Value: "TV"},
			},
		},
		File: []NZBFileSegment{
			{
				Subject:  fmt.Sprintf("Sample NZB for %s", filename),
				Poster:   "Fakearr <fakearr@example.com>",
				Date:     now,
				Groups:   []string{"alt.binaries.tv"},
				Segments: generateFakeSegments(filename),
			},
		},
	}

	// Encode to XML
	var buf bytes.Buffer
	encoder := xml.NewEncoder(&buf)
	encoder.Indent("", "  ")
	err := encoder.Encode(nzb)
	if err != nil {
		return nil, err
	}

	return buf.Bytes(), nil
}

// generateFakeSegments creates fake segments for an NZB file
func generateFakeSegments(filename string) []NZBSegment {
	segments := make([]NZBSegment, 10)
	for i := 0; i < 10; i++ {
		segments[i] = NZBSegment{
			Number:     i + 1,
			Size:       104857600, // 100 MB per segment
			SegmentRef: fmt.Sprintf("%s.%d@example.com", filename, i+1),
		}
	}
	return segments
}

// generateInfoHash creates a unique info hash based on pieces and filename
func generateInfoHash(pieces []byte, filename string) string {
	hash := sha1.New()
	hash.Write(pieces)
	hash.Write([]byte(filename))
	return string(hash.Sum(nil))
}

func main() {
	// Regex to match .torrent and .nzb files
	fileRegex := regexp.MustCompile(`^(.+)\.(torrent|nzb)$`)

	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		// Check if the request matches .torrent or .nzb pattern
		matches := fileRegex.FindStringSubmatch(r.URL.Path[1:])
		if matches == nil {
			http.NotFound(w, r)
			return
		}

		// Extract filename and file type
		originalFilename := matches[1]
		fileType := matches[2]

		// Log the requested file
		fmt.Printf("Generating %s for: %s\n", fileType, originalFilename)

		var (
			fileData []byte
			err      error
		)

		// Generate appropriate file type
		switch fileType {
		case "torrent":
			fileData, err = generateFakeTorrent(originalFilename)
			w.Header().Set("Content-Type", "application/x-bittorrent")
		case "nzb":
			fileData, err = generateFakeNZB(originalFilename)
			w.Header().Set("Content-Type", "application/x-nzb")
		}

		if err != nil {
			http.Error(w, fmt.Sprintf("Failed to generate %s", fileType), http.StatusInternalServerError)
			return
		}

		// Set disposition header
		w.Header().Set("Content-Disposition", fmt.Sprintf("attachment; filename=\"%s.%s\"", originalFilename, fileType))
		
		// Write file data
		_, err = io.Copy(w, bytes.NewReader(fileData))
		if err != nil {
			log.Printf("Error writing %s: %v", fileType, err)
		}
	})

	fmt.Println("Starting Fakearr on :8000")
	log.Fatal(http.ListenAndServe(":8000", nil))
}
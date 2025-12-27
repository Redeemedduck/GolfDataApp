# Video Frame Implementation Summary

## Overview

The GolfDataApp now supports downloading and displaying complete swing video sequences from Uneekor. Videos are delivered as individual frame images, providing frame-by-frame swing analysis.

## What Was Discovered

The Uneekor API provides swing videos as **24 individual frames** (topview00 through topview23):
- Each shot has 1 ballimpact image
- Each shot has 24 topview frames showing the complete swing sequence
- All frames are JPG images accessible via the same API endpoint

API Endpoint: `https://api-v2.golfsvc.com/v2/oldmyuneekor/report/shotimage/{report_id}/{key}/{session_id}/{shot_id}`

## Implementation Details

### 1. Flexible Video Download Strategy

**File**: `golf_scraper.py:155-257`

Added configurable `video_strategy` parameter to `upload_shot_images()`:

- **"none"**: Only first frame (minimal storage, current behavior)
- **"keyframes"**: 5 key frames (0, 6, 12, 18, 23) - RECOMMENDED DEFAULT
- **"half"**: Every other frame (12 frames)
- **"full"**: All 24 frames (maximum detail, 5x storage increase)

**Storage Impact**:
- Current: ~400KB/shot (impact + first frame)
- Keyframes: ~1.2MB/shot (impact + 5 frames)
- Half: ~2.5MB/shot (impact + 12 frames)
- Full: ~5MB/shot (impact + 24 frames)

With 380 shots:
- Current: ~152MB
- Keyframes: ~456MB (3x increase)
- Half: ~950MB (6.25x increase)
- Full: ~1.9GB (12.5x increase)

### 2. Database Schema Update

**File**: `golf_db.py:83-90, 133`

Added new column:
- `video_frames` (TEXT): Comma-separated list of video frame URLs

**Self-Healing Migration**: Database automatically adds this column on startup for existing databases.

### 3. Shot Viewer Video Playback

**File**: `app.py:298-331`

Added interactive video frame viewer:
- **Slider control**: Scrub through frames manually
- **Frame counter**: Shows current frame (e.g., "Frame 5/5")
- **Full-width display**: Each frame displayed at maximum size
- **Play button**: Placeholder for future auto-play feature

### 4. AI Coach Video Awareness

**File**: `app.py:476-497, 529-535`

Enhanced AI Coach capabilities:
- **Video Frame URLs**: AI can reference specific frames from `video_frames` column
- **Frame Analysis**: AI understands video sequences show complete swing mechanics
- **Capability List**: Added "Video Analysis" to AI capabilities

System prompt now includes:
```
**Available Media:**
- Impact Images: X shots have impact photos
- Swing Images: X shots have first-frame swing photos
- Video Frames: X shots have complete swing video sequences (multiple frames)
- Video frame URLs are in 'video_frames' column (comma-separated list)
```

## How to Use

### Import New Data with Videos

1. **Default (Keyframes Strategy)**:
   - Paste Uneekor URL in sidebar
   - Click "Run Scraper"
   - Videos will download with 5 key frames per shot

2. **Change Strategy**:
   Currently hardcoded to "keyframes" in `golf_scraper.py:107`

   To change, modify:
   ```python
   images = upload_shot_images(report_id, key, session_id, shot.get('id'), video_strategy="half")
   ```

### View Video Frames

1. Go to "Shot Viewer" tab
2. Click on any shot in the table
3. Scroll down to "📹 Swing Video Frames" section
4. Use slider to scrub through frames

### Ask AI About Videos

Example questions:
- "Analyze my swing sequence for shot #5"
- "What do the video frames show about my club path?"
- "Compare the impact position across different video frames"

## Files Modified

1. **golf_scraper.py**: Video download logic with configurable strategies
2. **golf_db.py**: Database schema migration for video_frames column
3. **app.py**: Video playback UI and AI Coach video awareness
4. **test_video_api.py**: Created for API research (can be deleted)

## Future Enhancements

1. **Auto-Play**: Implement true video playback with FPS control
2. **GIF Creation**: Stitch frames into animated GIF for sharing
3. **MP4 Encoding**: Convert frames to compressed video file
4. **Selective Download**: UI option to choose video strategy per import
5. **Frame Comparison**: Side-by-side frame comparison tool
6. **AI Vision Analysis**: Enable Gemini's vision capabilities to analyze swing mechanics from frames

## Testing

To test with new data:
1. Import a new Uneekor report URL
2. Check database for video_frames column: `sqlite3 golf_stats.db "SELECT shot_id, LENGTH(video_frames) FROM shots LIMIT 5;"`
3. Verify Supabase storage has multiple topview frames
4. Test Shot Viewer video scrubber
5. Ask AI Coach questions about video frames

## Technical Notes

- **Default Strategy**: "keyframes" provides best balance (3x storage for key swing moments)
- **Cloud Storage**: All frames uploaded to Supabase "shot-images" bucket
- **URL Format**: `{report_id}/{shot_id}_topviewXX.jpg` where XX is frame number
- **Backward Compatible**: Existing data without video_frames will still work
- **Performance**: Video frame slider loads one image at a time (no buffering yet)

## Storage Recommendations

For 1000 shots:
- **Keyframes (recommended)**: ~1.2GB total storage
- **Half**: ~2.5GB total storage (if you need more detail)
- **Full**: ~5GB total storage (only if analyzing every frame)

Supabase free tier: 1GB storage
- Keyframes: ~833 shots before upgrade needed
- Half: ~400 shots before upgrade needed
- Full: ~200 shots before upgrade needed

---

**Status**: ✅ Complete and deployed in Docker container
**Version**: Implemented December 21, 2024
**Testing Status**: Ready for user testing with new imports

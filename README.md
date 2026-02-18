# EloImage
Python script for ranking images using an Elo rating system.

Images are displayed in pairs and you vote for the better one. Elo ratings are stored directly in the filenames inside an `Elo` subfolder, making it trivial to sort the output by rating in any file browser.

## How to Use

1. Prepare a folder with images you want to rate. Supported formats: `.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp`, `.webp`.
2. Run the script by dragging and dropping the folder onto the script file, or from the command line:
   ```
   python EloImages.py "C:\path\to\your\image\folder"
   ```
3. The script creates an `Elo` subfolder, copies images there with an initial rating of 1000, and opens in fullscreen.

## Controls

| Key | Action |
|-----|--------|
| `←` / `→` | Vote for the left / right image |
| `Ctrl+←` / `Ctrl+→` | Delete the left / right image |
| `Space` | Skip the current pair |
| `Escape` | Exit |

## Voting

- After each vote the Elo ratings of both images are updated and the files are renamed accordingly.
- Pairs are chosen to prioritise images with the fewest matchups, ensuring a balanced distribution before any image is seen many times.
- If either image in the newly selected pair appeared in the previous pair, the script auto-skips up to 3 times to avoid back-to-back repeats.

## Deleting Images

Press `Ctrl+←` or `Ctrl+→` to mark an image for deletion. The selected image dims to 50% brightness and a confirmation dialog appears. Confirming removes the file from disk and from the competition entirely. If the pool drops to fewer than 2 images after a deletion the session ends gracefully.

This mode is useful for culling: repeatedly delete the weaker image until you are left with only the ones worth keeping.

## Progress Indicators

A small status area at the bottom centre shows two lines:

**Top line — image count**
```
42  —  5min 30sec
```
The number is how many images remain in the pool. The timer estimates how long it would take to finish if every remaining action is a deletion (one image removed per step).

**Bottom line — rating progress**
```
18 / 134  —  1h 2min 14sec
```
`A / B` where A is the total number of votes cast this session and B is the theoretical minimum number of votes needed to fully order N images (⌈log₂(N!)⌉). The timer estimates how long it would take to reach B if every remaining action is a vote.

Both timers are based on your average decision time in the current session only and update after every action. They naturally adapt to mixed delete+vote sessions.

## Session Resumption

Drag and drop the `Elo` subfolder (rather than the original folder) onto the script to resume a previous session. Ratings and matchup counts are loaded from `mappings.txt` inside the `Elo` folder.

## Notes

- `mappings.txt` in the `Elo` folder maps each image to its original filename and tracks its matchup count. The working copies are renamed frequently as ratings change, so the mapping file is what ties everything together.
- Debug information (pair selections, skip decisions) is printed to the console.

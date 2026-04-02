"""
Image Elo Rating System

This script allows you to rate images using an Elo rating system. The images are displayed in pairs,
and you vote for the better image. The script automatically updates the Elo ratings based on your votes.

How to Use:
1. Prepare a folder with images you want to rate. Supported formats are .png, .jpg, .jpeg, .gif, .bmp, and .webp.
2. Run the script by dragging and dropping the folder onto the script file, or by running the script from the command line with the folder path as an argument.
   Example: python EloImages.py "C:\\path\\to\\your\\image\\folder"
3. The script will create a subfolder named 'Elo' within your image folder and copy the images there with initial Elo ratings.
4. The images will be displayed in fullscreen mode, with two images side by side.
5. Use the arrow keys to vote for the better image:
   - Left Arrow: Vote for the left image
   - Right Arrow: Vote for the right image
   - Ctrl+Left: Delete the left image (with confirmation)
   - Ctrl+Right: Delete the right image (with confirmation)
   - Delete: Delete both images (with confirmation)
   - =: Toggle equalize mode (downscale larger image to match smaller's megapixels)
   - +/-: Zoom in/out by 10%
6. The Elo ratings will be updated after each vote, and the images will be renamed to reflect their current Elo ratings.
7. When deleting an image, the image will dim to indicate selection, and a confirmation dialog will appear.
   Confirming deletion counts as a vote for the surviving image (its Elo rating increases), then removes the
   deleted image from disk and from the competition. The progress indicator updates accordingly.
8. If the script detects that either of the images in the current pair was in the previous pair, it will automatically skip to a new pair.
9. You can manually skip a pair by pressing the Spacebar.
10. To exit the script, press the Escape key.
11. A small progress indicator appears at the bottom-center in the form "A / B": A is the total number of pairwise votes cast so far in this folder, and B is a theoretical lower bound on the number of pairwise votes needed to fully order n images, computed as ceil(log2(n!)). The numbers update after each vote.

Session Resumption:
- If you need to resume a session, drag and drop the 'Elo' folder onto the script. The script will load the existing ratings and continue from where you left off.

Note:
- Ensure that the folder path is valid and contains images.
- The script will display detailed debug information in the console, including comparisons and skip actions.
"""

import os
import sys
import time
import tkinter as tk
from PIL import Image, ImageTk, ImageEnhance
from tkinter import messagebox
import random
import string
import shutil
import math

class ImageEloApp:
    def __init__(self, root, folder_path):
        self.root = root
        self.folder_path = folder_path
        if folder_path.endswith('Elo'):
            self.elo_folder_path = folder_path
        else:
            self.elo_folder_path = os.path.join(folder_path, 'Elo')
        self.mappings_file = os.path.join(self.elo_folder_path, 'mappings.txt')
        self.images = []  # Stores paths to images in the Elo folder
        self.image_ratings = {}  # Maps Elo folder paths to ratings
        self.image_matchups = {}  # Maps Elo folder paths to number of matchups
        self.image_mappings = {}  # Maps Elo filenames to original filenames
        self.previous_pair = []  # Stores the previous pair of images for comparison
        self.current_pair = []  # Initialize to avoid attribute error
        self._deck = []  # Shuffled deck for round-robin image selection
        self._undo_state = None  # Stores state for 1-step undo
        self.session_action_count = 0
        self.session_total_duration = 0.0
        self.pair_display_time = None
        self._equalize_mode = False  # Downscale larger image to smaller's megapixels
        self._zoom_level = 1.0  # Canvas zoom multiplier

        self.setup_gui()
        if not os.path.isdir(self.elo_folder_path):
            os.makedirs(self.elo_folder_path)
        self.check_and_initialize()

    def setup_gui(self):
        self.root.title("Image Elo Rating")
        self.root.configure(bg='black')
        self.root.attributes('-fullscreen', True)
        self.root.bind('<Escape>', lambda e: self.root.quit())
        self.root.bind('<Right>', lambda e: self.vote_winner(1))
        self.root.bind('<Left>', lambda e: self.vote_winner(0))
        self.root.bind('<space>', lambda e: self.skip_matchup())  # Bind space key to skip feature
        self.root.bind('<Control-Left>', lambda e: self.confirm_delete(0))  # Delete left image
        self.root.bind('<Control-Right>', lambda e: self.confirm_delete(1))  # Delete right image
        self.root.bind('<BackSpace>', lambda e: self.undo())  # Undo last action
        self.root.bind('<Delete>', lambda e: self.confirm_delete_both())  # Delete both images
        self.root.bind('<equal>', lambda e: self.toggle_equalize())  # Equalize megapixels
        self.root.bind('<plus>', lambda e: self.zoom_in())  # Zoom in
        self.root.bind('<KP_Add>', lambda e: self.zoom_in())
        self.root.bind('<minus>', lambda e: self.zoom_out())  # Zoom out
        self.root.bind('<KP_Subtract>', lambda e: self.zoom_out())

        self.center_frame = tk.Frame(self.root, bg='black')
        self.center_frame.pack(expand=True)

        self.left_label = tk.Label(self.center_frame, bg='black')
        self.left_label.pack(side="left", padx=(0, 10), fill=tk.BOTH, expand=True)
        self.right_label = tk.Label(self.center_frame, bg='black')
        self.right_label.pack(side="right", padx=(10, 0), fill=tk.BOTH, expand=True)

        self.bottom_frame = tk.Frame(self.root, bg='black')
        self.bottom_frame.pack(side="bottom", fill=tk.X)
        self.count_label = tk.Label(self.bottom_frame, text="", fg="#666666", bg="black")
        self.count_label.pack(pady=(8, 0))
        self.progress_label = tk.Label(self.bottom_frame, text="", fg="#666666", bg="black")
        self.progress_label.pack(pady=(0, 8))

        # Corner indicators
        self.zoom_label = tk.Label(self.root, text="", fg="#666666", bg="black")
        self.zoom_label.place(relx=0.0, rely=1.0, anchor="sw", x=8, y=-8)
        self.equalize_label = tk.Label(self.root, text="", fg="#666666", bg="black")
        self.equalize_label.place(relx=1.0, rely=1.0, anchor="se", x=-8, y=-8)

    def check_and_initialize(self):
        if os.path.exists(self.mappings_file):
            self.load_mappings()
        else:
            self.populate_elo_folder()
        self.load_images()
        self.update_progress_label()

    def populate_elo_folder(self):
        alphabet = string.ascii_lowercase
        identifier_counter = 0
        with open(self.mappings_file, 'w') as f:
            for file in os.listdir(self.folder_path):
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')):
                    identifier = self.generate_identifier(identifier_counter, alphabet)
                    elo_path = os.path.join(self.elo_folder_path, f"1000_{identifier}{os.path.splitext(file)[1]}")
                    original_path = os.path.join(self.folder_path, file)
                    shutil.copy(original_path, elo_path)
                    self.image_mappings[elo_path] = original_path
                    self.image_matchups[elo_path] = 0  # Initialize matchup count
                    f.write(f"{file}::{identifier}::0\n")
                    identifier_counter += 1

    def load_mappings(self):
        with open(self.mappings_file, 'r') as f:
            for line in f:
                original_file, identifier, matchups = line.strip().split('::')
                base_dir = self.folder_path if not self.folder_path.endswith('Elo') else os.path.dirname(self.folder_path)
                original_path = os.path.join(base_dir, original_file)
                elo_files = [f for f in os.listdir(self.elo_folder_path) if f.endswith(f"_{identifier}{os.path.splitext(original_file)[1]}")]
                if elo_files:
                    elo_path = os.path.join(self.elo_folder_path, elo_files[0])
                    self.image_mappings[elo_path] = original_path
                    self.image_matchups[elo_path] = int(matchups)

    def generate_identifier(self, counter, alphabet):
        identifier = ''
        while counter >= 0:
            counter, remainder = divmod(counter, len(alphabet))
            identifier = alphabet[remainder] + identifier
            if counter == 0:
                break
        return identifier

    def load_images(self):
        for file in os.listdir(self.elo_folder_path):
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')):
                path = os.path.join(self.elo_folder_path, file)
                self.images.append(path)
                self.image_ratings[path] = int(file.split('_')[0])
        self.display_images()

    def _refill_deck(self):
        """Reshuffle all images into the deck, pushing recently-seen images to the end."""
        deck = list(self.images)
        random.shuffle(deck)
        # Move recently-shown images to the end so they appear last
        for img in self.previous_pair:
            if img in deck:
                deck.remove(img)
                deck.append(img)
        self._deck = deck

    def _draw_pair(self):
        """Draw two images from the shuffled deck, refilling when needed."""
        if len(self._deck) < 2:
            self._refill_deck()
        return [self._deck.pop(0), self._deck.pop(0)]

    def display_images(self, skip_attempts=0):
        if len(self.images) < 2:
            print("Not enough images to compare.")
            return

        self.current_pair = self._draw_pair()
        current_ids = [self.get_identifier(img) for img in self.current_pair]
        print(f"Selected pair: {current_ids}")  # Debug print

        self.previous_pair = self.current_pair
        self._refresh_display()
        self.pair_display_time = time.time()

    def _get_equalize_mp(self):
        """Return the target pixel count for equalize mode, or None if off."""
        if not self._equalize_mode or not self.current_pair:
            return None
        sizes = []
        for path in self.current_pair:
            with Image.open(path) as img:
                sizes.append(img.width * img.height)
        return min(sizes)

    def _refresh_display(self):
        """Re-render the current pair with current equalize/zoom settings."""
        if not self.current_pair:
            return
        equalize_mp = self._get_equalize_mp()
        self.update_image(self.left_label, self.current_pair[0], equalize_mp)
        self.update_image(self.right_label, self.current_pair[1], equalize_mp)

    def get_identifier(self, path):
        return os.path.splitext(os.path.basename(path))[0].split('_')[1]

    def update_image(self, label, image_path, equalize_mp=None, brightness=1.0):
        print("Updating image:", self.get_identifier(image_path))  # Debug statement
        img = Image.open(image_path)

        # Equalize: downscale larger image to match smaller's megapixels
        if equalize_mp is not None:
            native_mp = img.width * img.height
            if native_mp > equalize_mp:
                scale = math.sqrt(equalize_mp / native_mp)
                img = img.resize((max(1, int(img.width * scale)),
                                  max(1, int(img.height * scale))), Image.BILINEAR)

        # Fit to screen (no upscale at base zoom), then apply zoom
        base_w = self.root.winfo_screenwidth() // 2
        base_h = self.root.winfo_screenheight()
        ratio = min(base_w / img.width, base_h / img.height, 1.0)
        final_w = max(1, int(img.width * ratio * self._zoom_level))
        final_h = max(1, int(img.height * ratio * self._zoom_level))
        img = img.resize((final_w, final_h), Image.LANCZOS)

        if brightness != 1.0:
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(brightness)

        photo = ImageTk.PhotoImage(img)
        label.config(image=photo)
        label.image = photo

    def _record_action(self):
        if self.pair_display_time is not None:
            self.session_total_duration += time.time() - self.pair_display_time
            self.session_action_count += 1

    def _get_avg_seconds_per_action(self):
        if self.session_action_count == 0:
            return None
        return self.session_total_duration / self.session_action_count

    def format_duration(self, seconds):
        if seconds is None:
            return ""
        seconds = max(0, int(seconds))
        d, rem = divmod(seconds, 86400)
        h, rem = divmod(rem, 3600)
        m, s = divmod(rem, 60)
        parts = []
        if d: parts.append(f"{d}d")
        if h: parts.append(f"{h}h")
        if m: parts.append(f"{m}min")
        if s or not parts: parts.append(f"{s}sec")
        if d:  # drop seconds when estimate is in days
            parts = [p for p in parts if not p.endswith("sec")]
        return " ".join(parts)

    def min_votes(self, n: int) -> int:
        # exact, stable: log2(n!) = lgamma(n+1)/ln 2
        return math.ceil(math.lgamma(n + 1) / math.log(2))

    def compute_total_votes(self) -> int:
        # Each vote increments two images' matchup counters
        return (sum(self.image_matchups.values()) // 2) if self.image_matchups else 0

    def update_progress_label(self):
        n = len(self.images)
        a = self.compute_total_votes()
        b = self.min_votes(n) if n else 0
        avg = self._get_avg_seconds_per_action()

        del_timer = self.format_duration(avg * (n - 1)) if avg is not None else ""
        rating_timer = self.format_duration(avg * max(0, b - a)) if avg is not None else ""

        if hasattr(self, "count_label"):
            text = f"{n}"
            if del_timer:
                text += f"  —  {del_timer}"
            self.count_label.config(text=text)
        if hasattr(self, "progress_label"):
            text = f"{a} / {b}"
            if rating_timer:
                text += f"  —  {rating_timer}"
            self.progress_label.config(text=text)

    def skip_matchup(self, skip_attempts=0):
        print("Skipping matchup...")  # Debug print
        self.display_images(skip_attempts)

    def toggle_equalize(self):
        self._equalize_mode = not self._equalize_mode
        self.equalize_label.config(text="=" if self._equalize_mode else "")
        self._refresh_display()

    def zoom_in(self):
        self._zoom_level = round(self._zoom_level + 0.1, 1)
        self._update_zoom_label()
        self._refresh_display()

    def zoom_out(self):
        self._zoom_level = max(0.1, round(self._zoom_level - 0.1, 1))
        self._update_zoom_label()
        self._refresh_display()

    def _update_zoom_label(self):
        if self._zoom_level == 1.0:
            self.zoom_label.config(text="")
        else:
            self.zoom_label.config(text=f"{int(self._zoom_level * 100)}%")

    def undo(self):
        if self._undo_state is None:
            print("Nothing to undo.")
            return

        state = self._undo_state
        self._undo_state = None

        if state["type"] == "vote":
            self._undo_vote(state)
        elif state["type"] == "delete":
            self._undo_delete(state)
        elif state["type"] == "delete_both":
            self._undo_delete_both(state)

    def _undo_vote(self, state):
        # Rename files back to pre-vote paths
        for pre_path, post_path in zip(state["pre_paths"], state["post_paths"]):
            if pre_path != post_path:
                os.rename(post_path, pre_path)
                self.image_mappings[pre_path] = self.image_mappings.pop(post_path)
                self.image_ratings.pop(post_path)
                self.image_matchups.pop(post_path)
                self.images[self.images.index(post_path)] = pre_path
            self.image_ratings[pre_path] = state["pre_ratings"][pre_path]
            self.image_matchups[pre_path] = state["pre_matchups"][pre_path]

        self._deck = list(state["deck"])
        self.previous_pair = list(state["previous_pair"])
        self.session_action_count = state["session_action_count"]
        self.session_total_duration = state["session_total_duration"]
        self.update_mappings_file()
        self.update_progress_label()

        # Re-display the original pair
        self.current_pair = list(state["pre_paths"])
        self._refresh_display()
        self.pair_display_time = time.time()
        print(f"Undid vote. Restored pair: {[self.get_identifier(p) for p in self.current_pair]}")

    def _undo_delete(self, state):
        # Restore deleted file at its pre-vote path
        pre_path = state["deleted_pre_path"]
        with open(pre_path, 'wb') as f:
            f.write(state["file_bytes"])

        self.images.insert(state["deleted_index_in_images"], pre_path)
        self.image_ratings[pre_path] = state["deleted_pre_rating"]
        self.image_matchups[pre_path] = state["deleted_pre_matchups"]
        self.image_mappings[pre_path] = state["deleted_pre_mapping"]

        # Revert surviving image's rating boost
        surv_post = state["surviving_post_path"]
        surv_pre = state["surviving_pre_path"]
        if surv_post != surv_pre:
            os.rename(surv_post, surv_pre)
            self.image_mappings[surv_pre] = self.image_mappings.pop(surv_post)
            self.image_ratings.pop(surv_post)
            self.image_matchups.pop(surv_post)
            self.images[self.images.index(surv_post)] = surv_pre
        self.image_ratings[surv_pre] = state["surviving_pre_rating"]
        self.image_matchups[surv_pre] = state["surviving_pre_matchups"]

        self._deck = list(state["deck"])
        self.previous_pair = list(state["previous_pair"])
        self.session_action_count = state["session_action_count"]
        self.session_total_duration = state["session_total_duration"]
        self.update_mappings_file()
        self.update_progress_label()

        # Re-display the original pair
        self.current_pair = list(state["pair"])
        self._refresh_display()
        self.pair_display_time = time.time()
        print(f"Undid delete. Restored: {os.path.basename(pre_path)}")

    def _undo_delete_both(self, state):
        # Restore both files in original order (reverse so indices stay valid)
        for entry in reversed(state["entries"]):
            path = entry["deleted_path"]
            with open(path, 'wb') as f:
                f.write(entry["file_bytes"])
            self.images.insert(entry["index_in_images"], path)
            self.image_ratings[path] = entry["rating"]
            self.image_matchups[path] = entry["matchups"]
            self.image_mappings[path] = entry["mapping"]

        self._deck = list(state["deck"])
        self.previous_pair = list(state["previous_pair"])
        self.session_action_count = state["session_action_count"]
        self.session_total_duration = state["session_total_duration"]
        self.update_mappings_file()
        self.update_progress_label()

        self.current_pair = list(state["pair"])
        self._refresh_display()
        self.pair_display_time = time.time()
        names = [os.path.basename(p) for p in state["pair"]]
        print(f"Undid delete-both. Restored: {names[0]}, {names[1]}")

    def vote_winner(self, winner_index):
        if not self.current_pair:
            return

        # Capture pre-vote state for undo
        pair = list(self.current_pair)
        pre_ratings = {p: self.image_ratings[p] for p in pair}
        pre_matchups = {p: self.image_matchups[p] for p in pair}
        pre_deck = list(self._deck)
        pre_previous_pair = list(self.previous_pair)
        pre_action_count = self.session_action_count
        pre_duration = self.session_total_duration

        loser_index = 1 - winner_index
        winner = self.current_pair[winner_index]
        loser = self.current_pair[loser_index]
        self.image_matchups[winner] += 1
        self.image_matchups[loser] += 1
        self.update_elo_ratings(winner, loser)

        # Capture post-rename paths (rename_image updated self.current_pair)
        post_paths = list(self.current_pair)

        self.update_mappings_file()
        self._record_action()
        self.update_progress_label()
        self.display_images()

        self._undo_state = {
            "type": "vote",
            "pre_paths": pair,
            "post_paths": post_paths,
            "pre_ratings": pre_ratings,
            "pre_matchups": pre_matchups,
            "deck": pre_deck,
            "previous_pair": pre_previous_pair,
            "session_action_count": pre_action_count,
            "session_total_duration": pre_duration,
        }

    def update_elo_ratings(self, winner, loser, k=32):
        winner_rating = self.image_ratings[winner]
        loser_rating = self.image_ratings[loser]

        expected_winner = 1 / (1 + 10 ** ((loser_rating - winner_rating) / 400))
        expected_loser = 1 / (1 + 10 ** ((winner_rating - loser_rating) / 400))

        self.image_ratings[winner] += k * (1 - expected_winner)
        self.image_ratings[loser] += k * (0 - expected_loser)
        self.rename_image(winner, self.image_ratings[winner])
        self.rename_image(loser, self.image_ratings[loser])

    def rename_image(self, path, new_rating):
        dirname, filename = os.path.split(path)
        base_name, ext = os.path.splitext(filename)
        identifier = base_name.split('_')[1]
        new_filename = f"{int(new_rating)}_{identifier}{ext}"
        new_path = os.path.join(dirname, new_filename)
        os.rename(path, new_path)
        self.image_ratings[new_path] = self.image_ratings.pop(path)  # Update the ratings dictionary
        self.image_mappings[new_path] = self.image_mappings.pop(path)  # Update the mappings dictionary
        self.image_matchups[new_path] = self.image_matchups.pop(path)  # Update the matchups dictionary
        self.images[self.images.index(path)] = new_path  # Update the image list
        if path in self._deck:
            self._deck[self._deck.index(path)] = new_path  # Update the deck
        # Keep pair references current
        self.previous_pair = [new_path if p == path else p for p in self.previous_pair]
        self.current_pair = [new_path if p == path else p for p in self.current_pair]

    def update_mappings_file(self):
        with open(self.mappings_file, 'w') as f:
            for path, original_path in self.image_mappings.items():
                identifier = self.get_identifier(path)
                matchups = self.image_matchups[path]
                f.write(f"{os.path.basename(original_path)}::{identifier}::{matchups}\n")

    def confirm_delete(self, side_index):
        if not self.current_pair:
            return
        label = self.left_label if side_index == 0 else self.right_label
        side_name = "LEFT" if side_index == 0 else "RIGHT"

        # Dim the image to 50% brightness
        original_photo = label.image
        equalize_mp = self._get_equalize_mp()
        self.update_image(label, self.current_pair[side_index], equalize_mp, brightness=0.5)
        self.root.update()

        # Show confirmation dialog
        result = messagebox.askyesno("Confirm Delete", f"Delete the {side_name} image?")

        if result:
            self.delete_image(side_index)
        else:
            # Restore original image
            label.config(image=original_photo)
            label.image = original_photo

    def confirm_delete_both(self):
        if not self.current_pair:
            return

        # Dim both images to 50% brightness
        equalize_mp = self._get_equalize_mp()
        original_photos = [self.left_label.image, self.right_label.image]
        for side_index in range(2):
            label = self.left_label if side_index == 0 else self.right_label
            self.update_image(label, self.current_pair[side_index], equalize_mp, brightness=0.5)
        self.root.update()

        result = messagebox.askyesno("Confirm Delete", "Delete BOTH images?")

        if result:
            self.delete_both_images()
        else:
            # Restore original images
            self.left_label.config(image=original_photos[0])
            self.left_label.image = original_photos[0]
            self.right_label.config(image=original_photos[1])
            self.right_label.image = original_photos[1]

    def delete_both_images(self):
        pair = list(self.current_pair)

        # Capture undo state for both images
        undo_entries = []
        for image_path in pair:
            with open(image_path, 'rb') as f:
                file_bytes = f.read()
            undo_entries.append({
                "deleted_path": image_path,
                "file_bytes": file_bytes,
                "rating": self.image_ratings[image_path],
                "matchups": self.image_matchups[image_path],
                "mapping": self.image_mappings[image_path],
                "index_in_images": self.images.index(image_path),
            })

        undo = {
            "type": "delete_both",
            "pair": pair,
            "entries": undo_entries,
            "deck": list(self._deck),
            "previous_pair": list(self.previous_pair),
            "session_action_count": self.session_action_count,
            "session_total_duration": self.session_total_duration,
        }

        # Remove both from all data structures and disk
        for image_path in pair:
            self.images.remove(image_path)
            del self.image_ratings[image_path]
            del self.image_matchups[image_path]
            del self.image_mappings[image_path]
            if image_path in self._deck:
                self._deck.remove(image_path)
            os.remove(image_path)
            print(f"Deleted: {os.path.basename(image_path)}")

        self.update_mappings_file()

        if len(self.images) < 2:
            messagebox.showinfo("Session Complete", f"Only {len(self.images)} image(s) remaining. Exiting.")
            self.root.quit()
            return

        self.previous_pair = []
        self._record_action()
        self.update_progress_label()
        self.display_images()

        self._undo_state = undo

    def delete_image(self, side_index):
        deleted_path = self.current_pair[side_index]
        surviving_path = self.current_pair[1 - side_index]
        original_pair = list(self.current_pair)

        # Capture pre-vote state for undo
        pre_deleted_rating = self.image_ratings[deleted_path]
        pre_deleted_matchups = self.image_matchups[deleted_path]
        pre_deleted_mapping = self.image_mappings[deleted_path]
        pre_deleted_index = self.images.index(deleted_path)
        pre_surviving_path = surviving_path
        pre_surviving_rating = self.image_ratings[surviving_path]
        pre_surviving_matchups = self.image_matchups[surviving_path]
        pre_deck = list(self._deck)
        pre_previous_pair = list(self.previous_pair)
        pre_action_count = self.session_action_count
        pre_duration = self.session_total_duration

        # Count as a vote: surviving image wins, deleted image loses
        self.image_matchups[surviving_path] += 1
        self.image_matchups[deleted_path] += 1
        self.update_elo_ratings(surviving_path, deleted_path)

        # Paths changed due to rename — refresh from current_pair
        deleted_path = self.current_pair[side_index]
        surviving_path = self.current_pair[1 - side_index]

        # Read file bytes before deletion
        with open(deleted_path, 'rb') as f:
            file_bytes = f.read()

        undo = {
            "type": "delete",
            "pair": original_pair,
            "file_bytes": file_bytes,
            "deleted_pre_path": original_pair[side_index],
            "deleted_pre_rating": pre_deleted_rating,
            "deleted_pre_matchups": pre_deleted_matchups,
            "deleted_pre_mapping": pre_deleted_mapping,
            "deleted_index_in_images": pre_deleted_index,
            "surviving_post_path": surviving_path,
            "surviving_pre_path": pre_surviving_path,
            "surviving_pre_rating": pre_surviving_rating,
            "surviving_pre_matchups": pre_surviving_matchups,
            "deck": pre_deck,
            "previous_pair": pre_previous_pair,
            "session_action_count": pre_action_count,
            "session_total_duration": pre_duration,
        }

        # Remove from all data structures
        self.images.remove(deleted_path)
        del self.image_ratings[deleted_path]
        del self.image_matchups[deleted_path]
        del self.image_mappings[deleted_path]
        if deleted_path in self._deck:
            self._deck.remove(deleted_path)

        # Delete file from disk
        os.remove(deleted_path)
        print(f"Deleted: {os.path.basename(deleted_path)}")

        # Update mappings file
        self.update_mappings_file()

        # Check if enough images remain
        if len(self.images) < 2:
            messagebox.showinfo("Session Complete", f"Only {len(self.images)} image(s) remaining. Exiting.")
            self.root.quit()
            return

        # Clear previous pair to avoid skip issues and display new pair
        self.previous_pair = []
        self._record_action()
        self.update_progress_label()
        self.display_images()

        self._undo_state = undo

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Drag and drop the folder containing images onto this script.")
        sys.exit()

    folder_path = sys.argv[1]
    if not os.path.isdir(folder_path):
        print("Provided path is not a valid directory.")
        sys.exit()

    root = tk.Tk()
    app = ImageEloApp(root, folder_path)
    root.mainloop()

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
6. The Elo ratings will be updated after each vote, and the images will be renamed to reflect their current Elo ratings.
7. If the script detects that either of the images in the current pair was in the previous pair, it will automatically skip to a new pair.
8. You can manually skip a pair by pressing the Spacebar.
9. To exit the script, press the Escape key.

Session Resumption:
- If you need to resume a session, drag and drop the 'Elo' folder onto the script. The script will load the existing ratings and continue from where you left off.

Note:
- Ensure that the folder path is valid and contains images.
- The script will display detailed debug information in the console, including comparisons and skip actions.
"""

import os
import sys
import tkinter as tk
from PIL import Image, ImageTk
import random
import string
import shutil

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

        self.center_frame = tk.Frame(self.root, bg='black')
        self.center_frame.pack(expand=True)

        self.left_label = tk.Label(self.center_frame, bg='black')
        self.left_label.pack(side="left", padx=(0, 10), fill=tk.BOTH, expand=True)
        self.right_label = tk.Label(self.center_frame, bg='black')
        self.right_label.pack(side="right", padx=(10, 0), fill=tk.BOTH, expand=True)

    def check_and_initialize(self):
        if os.path.exists(self.mappings_file):
            self.load_mappings()
        else:
            self.populate_elo_folder()
        self.load_images()

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
                original_path = os.path.join(os.path.dirname(self.folder_path), original_file)
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

    def display_images(self, skip_attempts=0):
        if len(self.images) < 2:
            print("Not enough images to compare.")
            return

        min_matchups = min(self.image_matchups.values())
        candidate_images = [img for img in self.images if self.image_matchups[img] == min_matchups]

        # Relax criteria if there are not enough candidates
        if len(candidate_images) < 2:
            next_min_matchups = min(val for val in self.image_matchups.values() if val > min_matchups)
            candidate_images += [img for img in self.images if self.image_matchups[img] == next_min_matchups]

        self.current_pair = random.sample(candidate_images, 2)
        current_ids = [self.get_identifier(img) for img in self.current_pair]
        previous_ids = [self.get_identifier(img) for img in self.previous_pair]
        print(f"Selected pair: {current_ids}")  # Debug print

        skip_needed = False
        checks = []
        for cur_img in current_ids:
            for prev_img in previous_ids:
                check = f"is {cur_img} = {prev_img}? {'yes' if cur_img == prev_img else 'no'}"
                checks.append(check)
                if cur_img == prev_img:
                    skip_needed = True
        for check in checks:
            print(check)  # Print each comparison
        if skip_needed and skip_attempts < 3:
            print("Skipping due to match with previous pair")
            self.skip_matchup(skip_attempts + 1)
            return

        self.previous_pair = self.current_pair
        print("Current pair after check:", current_ids)  # Debug statement
        self.update_image(self.left_label, self.current_pair[0])
        self.update_image(self.right_label, self.current_pair[1])

    def get_identifier(self, path):
        return os.path.splitext(os.path.basename(path))[0].split('_')[1]

    def update_image(self, label, image_path):
        print("Updating image:", self.get_identifier(image_path))  # Debug statement
        img = Image.open(image_path)
        img.thumbnail((self.root.winfo_screenwidth() // 2, self.root.winfo_screenheight()), Image.LANCZOS)
        photo = ImageTk.PhotoImage(img)
        label.config(image=photo)
        label.image = photo

    def skip_matchup(self, skip_attempts=0):
        print("Skipping matchup...")  # Debug print
        self.display_images(skip_attempts)

    def vote_winner(self, winner_index):
        if not self.current_pair:
            return
        loser_index = 1 - winner_index
        winner = self.current_pair[winner_index]
        loser = self.current_pair[loser_index]
        self.image_matchups[winner] += 1
        self.image_matchups[loser] += 1
        self.update_elo_ratings(winner, loser)
        self.update_mappings_file()
        self.display_images()

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

    def update_mappings_file(self):
        with open(self.mappings_file, 'w') as f:
            for path, original_path in self.image_mappings.items():
                identifier = self.get_identifier(path)
                matchups = self.image_matchups[path]
                f.write(f"{os.path.basename(original_path)}::{identifier}::{matchups}\n")

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

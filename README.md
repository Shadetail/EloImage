# EloImage
Phyton script for ranking images using Elo rating system.

This script allows you to rate images using an Elo rating system. The images are displayed in pairs,
and you vote for the better image using left and right arrow. The script automatically updates the Elo ratings based on your votes. Images are duplicated in an Elo subfolder and Elo rating is stored in image file names to make it easy to sort images by their Elo rating.

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
7. If the script detects that either of the images in the current pair was in the previous pair, it will automatically skip to a new pair. Maximum of 3 auto skips in a row to prevent infinite loop.
8. You can manually skip a pair by pressing the Spacebar.
9. To exit the script, press the Escape key.

Session Resumption:
- If you need to resume a session, drag and drop the 'Elo' folder onto the script. The script will load the existing ratings and continue from where you left off.

Note:
- Mappings.txt file will be placed in the Elo folder as well. It is used to map original images to images inside of Elo folder since we don't want to display images that are being constantly renamed as that leads to trouble. This file is also used to store the number of matchups that each image had, in order to proide a more balanced pseudorandom choice of images (to avoid randomizing the same image many times while almost never randomizing some other image).
- The script will display detailed debug information in the console, including comparisons and skip actions.
- I made this using GPT4 and GPT4o, took around 10 hours.

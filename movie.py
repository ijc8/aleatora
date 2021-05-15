# Import everything needed to edit video clips
from moviepy.editor import *

# Load myHolidays.mp4 and select the subclip 00:00:50 - 00:00:60
clip = VideoFileClip("/home/ian/Videos/performance.mp4").subclip(50,60)

# Reduce the audio volume (volume x 0.8)
clip = clip.volumex(0.8)

# Generate a text clip. You can customize the font, color, etc.
txt_clip = (TextClip("My Holidays 2013",fontsize=70,color='white')
            .set_start(5)
            .set_duration(10)
            .set_position('center'))

# Overlay the text clip on the first video clip
video = CompositeVideoClip([clip, txt_clip])

# Write the result to a file (many options available !)
video.write_videofile("performance_edited.webm")

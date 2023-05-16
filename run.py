# Import the required modules
import sys, os
import pydub
import openai
import srt
import moviepy.editor as mp
from moviepy.video.tools.subtitles import SubtitlesClip

# Set the OpenAI API key
openai.api_key = os.environ.get("OPENAI_KEY")

audio_segment_size_in_mb = lambda audio_segment:  audio_segment.frame_count() * audio_segment.frame_width / (1024 * 1024)

# Define a function to transcribe an audio segment using OpenAI
def transcribe(segment):
  # Convert the segment to wav format and save it to a temporary file
  segment.export("temp.wav", format="wav")
  # Open the file in binary mode
  with open("temp.wav", "rb") as f:
    # Call the OpenAI speech to text API and get the response
    response = openai.Audio.transcribe('whisper-1', f)
  # Return the transcription text
  return response["text"]

# def split_on_silence_or_half(segment):
#   if audio_segment_size_in_mb(segment) > 25:


# Define a recursive function to split and transcribe a segment until its text is less than 61 characters
def split_and_transcribe(segment, start, end, transcriptions):
  # Transcribe the segment using OpenAI
  text = transcribe(segment)
  # Check the length of the text in characters
  if len(text) > 61:
    # If the length is greater than 61, split the segment in half and call the function on each part again
    half = len(segment) // 2
    part1 = segment[:half]
    part2 = segment[half:]
    split_and_transcribe(part1, start, start + half, transcriptions)
    split_and_transcribe(part2, start + half, end, transcriptions)
  else:
    # If the length is less than or equal to 61, store the segment and its transcription in the transcriptions list
    transcriptions.append((start, end, text))

# Get the path to the audio or video file from the command-line argument
path = sys.argv[1]

# Load the file using pydub and get its audio
audio = pydub.AudioSegment.from_file(path)

size_in_mb = audio_segment_size_in_mb(audio)

# Split the audio into segments
if size_in_mb > 25:
  segments = pydub.silence.split_on_silence(audio)
else:
  segments = [audio]

# Initialize an empty list to store the transcriptions and their start and end times
transcriptions = []

# Initialize the start time as zero
start = 0
# Loop through each segment
for segment in segments:
  # Get the end time of the segment by adding its length to the start time
  end = start + len(segment)
  # Call the recursive function to split and transcribe the segment until its text is less than 61 characters
  split_and_transcribe(segment, start, end, transcriptions)
  # Update the start time for the next segment
  start = end

# Initialize an empty list to store the SRT subtitles
subtitles = []

# Loop through each transcription
for i, (start, end, text) in enumerate(transcriptions):
  # Create a SRT subtitle object with the index, start time, end time and text
  subtitle = srt.Subtitle(index=i+1, start=srt.timedelta(milliseconds=start), end=srt.timedelta(milliseconds=end), content=text)
  # Append it to the subtitles list
  subtitles.append(subtitle)

# Generate a SRT file from the subtitles list
srt_file = srt.compose(subtitles)

# Save the SRT file with the same name as the original file but with .srt extension
srt_path = path.rsplit(".", 1)[0] + ".srt"
with open(srt_path, "w") as f:
  f.write(srt_file)

# Load the original file using moviepy and attach the SRT file to it using moviepy's subclip method
clip = mp.VideoFileClip(path).subclip()
generator = lambda txt: mp.TextClip(txt, font='Georgia-Regular', fontsize=24, color='white')
clip_with_subtitles = mp.CompositeVideoClip([clip, SubtitlesClip(srt_path).set_position(("center", "bottom"))])
# Export the clip with subtitles in the same format as before using moviepy's write_videofile method
clip_with_subtitles.write_videofile(path)
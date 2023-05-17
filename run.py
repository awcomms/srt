# Import the required modules
import sys, os, io
import pydub
import openai
import srt

segment_limit = 21

# Set the OpenAI API key
openai.api_key = os.environ.get("OPENAI_KEY")

# splits an audio segment into chunks of a given size limit
def split_audio_to_size(audio, size_limit):
    # Convert the size limit from mb to bytes
    max_size = size_limit * 1024 * 1024

    # Define an empty list to store the chunks
    chunks = []

    # Loop until the audio segment is empty
    while len(audio) > 0:
        # Calculate the bitrate of the audio segment in bytes per millisecond
        bitrate = audio.frame_rate * audio.frame_width * audio.channels / 1000

        # Calculate the maximum duration of each chunk in milliseconds
        max_duration = max_size / bitrate

        # Split the audio segment into a chunk and the remaining part
        chunk, audio = audio[:max_duration], audio[max_duration:]

        # Append the chunk to the list of chunks
        chunks.append(chunk)

    # Return the list of chunks
    return chunks

audio_segment_size_in_mb = lambda audio_segment:  audio_segment.frame_count() * audio_segment.frame_width / (1024 * 1024)

# Define a function to transcribe an audio segment using OpenAI
def transcribe(segment):
  # Convert the segment to wav format and save it to an in-memory file-like object
  file_like_object = io.BytesIO()
  setattr(file_like_object, "name", "audio.wav")
  segment.export(file_like_object, format="wav")
  file_like_object.seek(0)  # reset file pointer to the beginning
  # Call the OpenAI speech to text API and get the response
  response = openai.Audio.transcribe('whisper-1', file_like_object)
  # Return the transcription text
  return response["text"]

# def split_on_silence_or_half(segment):
#   if audio_segment_size_in_mb(segment) > segment_limit:

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
if size_in_mb > segment_limit:
  segments = split_audio_to_size(audio, segment_limit)
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

new_path = path.rsplit(".", 1)[0] + "_subtitled.mp4"
os.system (f"ffmpeg -i {path} -i {srt_path} -c:v copy -c:a copy -c:s mov_text {new_path}")
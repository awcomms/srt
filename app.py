from flask import Flask, request, send_file
from .methods import single_transcription, create_srt, subtitle
app = Flask(__name__)

@app.route('/', methods=['POST'])
def transcribe():
    file = request.files.get('file')
    mode = request.args.get('mode')
    file.save(file.filename)
    if file:
        if mode == "text":
            return single_transcription(file.filename)
        elif mode == "srt":
            return create_srt(file.filename)
        elif mode == "subtitle":
            return send_file(subtitle(file.filename), as_attachment=True)
        else:
            return "Required `mode` argument must be one of `text`, `srt` or `subtitle`"
    else:
        return "No file uploaded"
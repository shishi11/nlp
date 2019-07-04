import ffmpeg
import pprint
info = ffmpeg.probe("resources/414796e077d6492ebd54e22075ea0107.mp4")
pprint.pprint(info)
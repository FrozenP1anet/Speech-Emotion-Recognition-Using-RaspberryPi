#!/bin/bash

# lxterminal -e "bash -c 'echo 1 && exec bash'"
lxterminal -e "cd /home/pi/my_prj/Speech_Emotion_Recognition_prj1215 && \
	       sudo /home/pi/miniconda3/bin/python3 ./example.py"

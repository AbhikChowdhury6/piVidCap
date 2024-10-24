import pandas as pd
import os
import sys

cwd = os.getcwd()
delimiter = "\\" if "\\" in cwd else "/"
repoPath = delimiter.join(cwd.split(delimiter)[:cwd.split(delimiter).index("videoProcessing")]) + delimiter

workingDataPath = repoPath + "workingVideoData/"
videoDataPath = repoPath + 'videoFiles/'
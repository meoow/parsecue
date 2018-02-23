#!/usr/bin/env python2.7

import sys
import parsecue_lib as pcue

cue = pcue.parsecue(sys.argv[1])
pcue.ffmpeg(cue, ['-af', 'silenceremove=1:0:-75dB:1:1:-75dB,adelay=200|200', '-c:a', 'aac', '-strict', '-2', '-b:a', '480k'], 'm4a')

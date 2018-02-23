#!/usr/bin/env python2.7

import sys
import parsecue_lib as pcue

cue = pcue.parsecue(sys.argv[1])
pcue.ffmpeg_mt(cue, ['-af', 'silenceremove=1:0:-75dB:1:1:-75dB,adelay=200|200','-c:a', 'flac', '-compression_level','12', '-sample_fmt', 's16'], 'flac')

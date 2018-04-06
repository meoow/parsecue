#!/usr/bin/env python2.7

import sys
import parsecue_lib as pcue

for c in sys.argv[1:]:
	cue = pcue.parsecue(c)
	pcue.ffmpeg_mt(cue, ['-vn', '-c:a', 'alac', '-f', 'ipod'], 'm4a')

#!/usr/bin/env python2.7

import sys
import parsecue_lib as pcue

for c in sys.argv[1:]:
	cue = pcue.parsecue(c)
	pcue.ffmpeg_mt(cue, ['-c:a', 'flac', '-compression_level','12'], 'flac')

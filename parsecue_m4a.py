#!/usr/bin/env python2.7

import sys
import parsecue_lib as pcue

cue = pcue.parsecue(sys.argv[1])
pcue.ffmpeg_mt(cue, ['-c:a', 'aac', '-strict', '-2', '-b:a', '480k'], 'm4a')

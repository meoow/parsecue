#!/usr/bin/env python2.7

#!/usr/bin/env python2.7

import subprocess as subp
import sys
import os
import os.path
from os.path import splitext, basename, dirname
import random
import parsecue_lib as pcue
import re
import copy
import tempfile

sys.path.append(os.path.join(dirname(__file__), 'mutagen.zip'))
import mutagen

if os.path.dirname(sys.argv[1]):
	os.chdir(os.path.dirname(sys.argv[1]))
cue = pcue.parsecue(os.path.basename(sys.argv[1]))

if not os.path.isfile(cue['filename']):
	raise IOError("Can't not find file")

fstat = os.stat(cue['filename'])
fmeta = mutagen.File(cue['filename'])
atime = fstat.st_atime
mtime = fstat.st_mtime
devnull = open(os.devnull, 'wb')

for idx,i in cue['tracks'].iteritems():

	output = re.sub(r'[/\?\'":]','_',cue.get('disc', '')+idx+' - '+i.get('title', ''))+'.m4a'
	tmpfilewav = tempfile.mktemp()

	s_n = pcue.ts1(cue, idx)
	start_dt = pcue.duration2secs(s_n[0], True)
	end_dt = pcue.duration2secs(s_n[1], True)
	dura = str((end_dt - start_dt).total_seconds())

	try:
		print output
		subp.check_call(['ffmpeg','-v', 'error', '-hide_banner', '-ss', s_n[0], '-i', cue['filename'], '-ss', '0', '-t', dura, '-af', 'silenceremove=1:0:-70dB:1:1:-70dB:window=0.01,adelay=200|200', '-c:a', 'pcm_s16le', '-f', 'wav', tmpfilewav])
		subp.check_call(['afconvert', '-d', 'aac', '-f', 'm4af', '-s', '3', '-q', '127', '-u', 'vbrq', '127', tmpfilewav, output])
		ometa = mutagen.File(output)
		for k,v in fmeta.iteritems():
			if k.lower() == 'cuesheet':
				continue
			ometa[k] = ';'.join(v).encode('utf8')
			ometa['----:com.apple.iTunes:{}'.format(k)] = ';'.join(v).encode('utf8')
		for i in pcue.metadata(cue, idx):
			if i == '-metadata':
				continue
			k, v = i.split('=', 1)
			k = k.encode('utf8')
			v = v.encode('utf8')
			ometa[k] = v
			ometa['----:com.apple.iTunes:{}'.format(k)] = v
		ometa.save()
		os.utime(output, (atime, mtime))
	finally:
		if os.path.exists(tmpfilewav):
			os.unlink(tmpfilewav)

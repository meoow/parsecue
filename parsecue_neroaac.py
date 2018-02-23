#!/usr/bin/env python2.7

import subprocess as subp
import sys
import os
from os.path import splitext, basename
import random
import glob
import parsecue_lib as pcue
import threading
import re
import copy

standard_tags = {
"title":True,
"artist":True,
"year":True,
"album":True,
"genre":True,
"track":True,
"totaltracks":True,
"disc":True,
"totaldiscs":True,
"url":True,
"copyright":True,
"comment":True,
"lyrics":True,
"credits":True,
"rating":True,
"label":True,
"composer":True,
"isrc":True,
"mood":True,
"tempo":True}

def ffmeta2nerometa(metalist):
	for t in (i for i in metalist if i != '-metadata'):
		k,v = t.split('=', 1)
		if k in standard_tags:
			yield u'-meta:{0}={1}'.format(k, v)
		elif k == 'disctotal':
			yield u'-meta:totaldisc={0}'.format(v)
		elif k == 'tracktotal':
			yield u'-meta:totaltracks={0}'.format(v)
		else:
			yield u'-meta-user:{0}={1}'.format(k, v)

if os.path.dirname(sys.argv[1]):
	os.chdir(os.path.dirname(sys.argv[1]))
cue = pcue.parsecue(os.path.basename(sys.argv[1]))

if not os.path.isfile(cue['filename']):
	raise IOError("Can't not find file")

fstat = os.stat(cue['filename'])
atime = fstat.st_atime
mtime = fstat.st_mtime
devnull = open(os.devnull, 'wb')

for idx,i in cue['tracks'].iteritems():

	output = re.sub('[/\?\'"]','_',cue.get('disc', '')+idx+' - '+i.get('title', ''))+'.m4a'

	s_n = pcue.ts0(cue, idx)
	start_dt = pcue.duration2secs(s_n[0], True)
	end_dt = pcue.duration2secs(s_n[1], True)
	dura = str((end_dt - start_dt).total_seconds())

	#cmd0 = ['ffmpeg', '-hide_banner', '-v', 'error', '-f','lavfi','-t', '0.2', '-i','anullsrc=r=44100:cl=stereo', '-ss', s_n[0], '-i', cue['filename'], '-ss', '0', '-t', dura, '-lavfi', '[1:a]silenceremove=1:0:-70dB:window=0.015[a1];[0:a][a1]concat=v=0:a=1[a2]', '-map', '[a2]', '-c:a', 'pcm_s32le', '-f', 'wav', '-']
	#cmd0 = ['ffmpeg', '-hide_banner', '-v', 'error', '-ss', s_n[0], '-i', cue['filename'], '-ss', '0', '-t', dura, '-af', 'silenceremove=1:0:-70dB', '-c:a', 'pcm_s32le', '-f', 'wav', '-']
	cmd0 = ['ffmpeg', '-hide_banner', '-v', 'error', '-ss', s_n[0], '-i', cue['filename'], '-ss', '0', '-t', dura, '-af', 'silenceremove=1:0:-70dB:1:1:-70dB:window=0.01,adelay=200|200', '-c:a', 'pcm_s32le', '-f', 'wav', '-']

	print output
	p1 = subp.Popen(cmd0, stdout=subp.PIPE)
	subp.check_call(['wine', 'neroaacenc.exe', '-ignorelength', '-if', '-', '-of', output, '-q', '1'], stdin=p1.stdout, stderr=devnull)
	subp.check_call(['wine', 'neroaactag.exe']+list(ffmeta2nerometa(pcue.metadata(cue, idx)))+[output], stderr=devnull)
	os.utime(output, (atime, mtime))

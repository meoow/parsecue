#!/usr/bin/false

from collections import OrderedDict
from os.path import splitext, basename
import datetime
import glob
import os
import os.path
import pprint
import random
import re
import subprocess as subp
import sys
import copy

ENCODING_LIST = ('utf-8','cp936', 'euc-kr', 'shift-jis', 'big5')

def slicein(sub, lst):
	if len(sub) > len(lst):
		return False
	if sub == lst[:len(sub)]:
		return True
	else:
		return slicein(sub, lst[1:])

def parsDiscNum(title):
	ptn1 = r'(?<=[^\w]| )\[dis[ck](?:\s+)?(\d+|[A-Z])\]$'
	ptn2 = r'(?<=[^\w]| )dis[ck](?:\s+)?(\d+|[A-Z])$'
	ptn3 = r'(?<=[^\w]| )\(CD\s?(\d+)\)$'
	ptn4 = r'(?<=[^\w]| )CD\s?(\d+)$'
	for ptn in (ptn1, ptn2, ptn3, ptn4):
		d = re.search(ptn, title, flags=re.I)
		if d is None:
			continue
		title = re.sub(ptn, '', title, flags=re.I)
		if re.match(r'\d', d.group(1)):
			dn = d.group(1).lstrip('0')
		else:
			dn = str(ord(d.group(1).upper())-64)
		return (title, dn)
	return (None, None)

def duration2secs(timestr, return_dt=False):
	tptn = re.compile('^(?:(\d+)(?:\.(\d{1,3}))?|(?:(?:(\d{2}):)?(0{1,2}|0?[1-9]|[1-5][0-9]):)?(0{1,2}|0?[1-9]|[1-5][0-9])(?:\.(\d{1,3}))?)$')
	mat = tptn.match(timestr)
	h=0; min_=0; sec=0; millisec=0
	if mat is not None:
		if any(mat.groups()[:2]):
			if mat.group(1) is not None:
				sec = int(mat.group(1))
			if mat.group(2) is not None:
				millisec = int('{:0<3s}'.format(mat.group(2)))
		elif any(mat.groups()[2:]):
			if mat.group(3) is not None:
				h = int(mat.group(3))
			if mat.group(4) is not None:
				min_ = int(mat.group(4))
			if mat.group(5) is not None:
				sec = int(mat.group(5))
			if mat.group(6) is not None:
				millisec = int('{:0<3s}'.format(mat.group(6)))
		dt = datetime.timedelta(hours=h, minutes=min_, seconds=sec, milliseconds=millisec)
		if return_dt:
			return dt
		else:
			return str(dt.total_seconds())

	raise ValueError('Invalid duration string: {}'.format(timestr))

def avgTimePoint(a, b):
	aa = a.split(':')
	bb = b.split(':')
	cc = [0, 0, 0]
	for idx, (x, y) in enumerate(izip(aa, bb)):
		cc[idx] = (int(y) + int(x))/2
	return ':'.join(str(i) for i in cc)


def parsecue(cuefile):

	filecontent = open(cuefile).read()

	for enc in ENCODING_LIST:
		try:
			filecontent = filecontent.decode(enc)
			encoding = enc
			break
		except UnicodeDecodeError as e:
			if enc == ENCODING_LIST[-1]:
				raise e
			else:
				pass
	
	output = {}
	head, filename, trax = re.split(r'\s*FILE\s+"([^"]+)"\s+.+?\r?\n', filecontent,maxsplit=2)
	#print trax
	if head.startswith(u'\ufeff'):
		head=head[1:]

	recs = re.split(r'\s*TRACK\s+(\d+)\s+AUDIO\s*\r?\n',trax[trax.index('TRACK'):])[1:]

	for l in head.split('\n'):
		l = l.strip()
		l = re.sub(r'^REM\s+', '', l)
		m = re.match(r'^(TITLE|PERFORMER|YEAR|COMMENT|GENRE|ARTIST|TRACKTOTAL|DATE|DISC|DISCTOTAL|DISCID|COMPOSER)\s+(.+)$', l)
		if m:
			output[m.group(1).lower()] = m.group(2).strip('"\'')
	
	if 'date' in output and 'year' not in output:
		output['year'] = re.match(r'^\d{4}',output['date']).group(0)
	
	if 'title' in output and 'album' not in output:
		output['album'] = output['title']

	if 'album' in output and 'disc' not in output:
		title, dn = parsDiscNum(output['album'])
		if title is not None:
			output['album'] = title
			output['disc']  = dn

	if not os.path.isfile(filename):
		for i in glob.glob(os.path.splitext(filename)[0] + '.*'):
			if os.path.splitext(i)[1] in ('.ape', '.flac','.tta', '.wv', '.wav', '.mp3'):
				filename = i
	output['filename'] = filename
	records = OrderedDict()
	for idx in xrange(0, len(recs), 2):
		trackNum = recs[idx]
		rawMeta  = recs[idx+1]
		record = {}
		for entry in re.split(r'\s*\r?\n\s*', rawMeta.strip()):
			m1 = re.match(r'''(TITLE|PERFORMER|YEAR|COMMENT|GENRE|ARTIST|COMPOSER)\s+"(.+)"''', entry)
			if m1:
				record[m1.group(1).lower()] = m1.group(2)
				continue
			m2 = re.match(r'INDEX\s+(00|01)\s+(\d+:\d+:\d+)', entry)
			if m2:
				invalidTime = [int(i) for i in m2.group(2).split(':')]
				if len(invalidTime) == 3:
					invalidTime.insert(0, 0)
				if invalidTime[2] > 59:
					invalidTime[1] = invalidTime[1] + invalidTime[2]/60
					invalidTime[2] = invalidTime[2]%60
				if invalidTime[1] > 59:
					invalidTime[0] = invalidTime[0] + invalidTime[1]/60
					invalidTime[1] = invalidTime[1]%60
				record['index'+m2.group(1)] = ':'.join('{0:02d}'.format(i) for i in invalidTime[:3])+'.{0:<03d}'.format(invalidTime[3])
				continue

		records[trackNum] = record

	trackNumList = sorted(records.iterkeys())
	for c, i in enumerate(trackNumList):
		if c == 0:
			continue
		records[trackNumList[c-1]]['end'] = records[i].get('index00',records[i]['index01'])
	records[trackNumList[-1]]['end'] = '99:59:59'
	
	output['tracks']   = records

	if 'tracktotal' not in output:
		output['tracktotal'] = len(output['tracks'])
	output['slashtracktotal'] = '/{0}'.format(output['tracktotal'])

	return output

def ts1(cue, idx):
	i = cue['tracks'][idx]
	return [i.get('index01', i.get('index00', None)), i['end']]

def ts0(cue, idx):
	i = cue['tracks'][idx]
	return [i.get('index00', i.get('index01', None)), i['end']]

def metadata(cue, idx):

	i = cue['tracks'][idx]

	cmd = [
	u'title={0}'.format(i.get('title', "")), 
	u'artist={0}'.format(i.get('artist', cue.get('artist', i.get('performer', cue.get('performer', ''))))),
	u'author={0}'.format(i.get('artist', cue.get('artist', i.get('performer', cue.get('performer', ''))))),
	u'album_artist={0}'.format(cue.get('artist', i.get('artist', i.get('performer', cue.get('performer', ''))))),
	u'performer={0}'.format(i.get('performer', cue.get('performer', ''))),
	u'album={0}'.format(i.get('album', cue.get('album', ''))), 
	u'year={0}'.format(i.get('year', cue.get('year', cue.get('date', '').split('/')[0]))), 
	u'date={0}'.format(i.get('date', cue.get('date', ''))), 
	u'genre={0}'.format(i.get('genre', cue.get('genre', ''))), 
	u'track={0}'.format(idx.lstrip('0')), 
	u'tracknumber={0}'.format(idx.lstrip('0')), 
	u'tracktotal={0}'.format(cue['tracktotal']), 
	u'totaltracks={0}'.format(cue['tracktotal']), 
	u'disc={0}'.format(cue.get('disc', '')) , 
	u'discid={0}'.format(i.get('discid', '')), 
	u'disctotal={0}'.format(cue.get('disctotal', '')), 
	u'totaldiscs={0}'.format(cue.get('disctotal', '')), 
	 u'composer={0}'.format(i.get('composer', cue.get('composer', '')))
	]
	return [ b for a in (('-metadata',x) for x in cmd if re.match(r'^[^=]+=$', x) is None ) for b in a ]+['-metadata', 'cuesheet=']

def ffmpeg_mt(cue, encoderArgs, extname):

	if not os.path.isfile(cue['filename']):
		raise IOError("Can't not find file")

	fstat = os.stat(cue['filename'])
	atime = fstat.st_atime
	mtime = fstat.st_mtime
	
	for ids in (cue['tracks'].keys()[i:i+8] for i in range(0,len(cue['tracks']),8)):
		cmds = []
		outputs = []
		cmd = ['ffmpeg', '-y', '-hide_banner', '-f', 'lavfi', '-i', 'aevalsrc=0|0:d=1:s=44100,aformat=sample_fmts=s16,atrim=start=0:end=0.333', '-i', cue['filename']]
		for idx in ids:
			i = cue['tracks'][idx]
			enc = copy.copy(encoderArgs)
			output = re.sub('[/\?\'"]','_',cue.get('disc', '')+idx+' - '+i.get('title', ''))+'.'+extname.lstrip('. ')
			s0, e0 = ts0(cue, idx)
			s1, e1 = ts1(cue, idx)
			start_dt  = (duration2secs(s1, True) - duration2secs(s0, True)) / 3 * 2 + duration2secs(s0, True)
			end_dt = duration2secs(e1, True)
			atrim = '[1:a]atrim=start={0}:end={1}[a0];[a0]silenceremove=1:0:-82dB:1:1:-82dB[a1];[0][a1]concat=n=2:a=1:v=0[astream]'.format(start_dt.total_seconds(), end_dt.total_seconds())
			enc = ['-lavfi', atrim, '-map', '[astream]']+enc
			cmd.extend(enc+metadata(cue, idx))
			cmd.append(output)
			outputs.append(output)

		if extname == "m4a" or slicein(['-f', 'ipod'], cmd):
			trackptn = re.compile(r'^track=\d+$')
			for idx, i in enumerate(cmd):
				if i == '-metadata' and trackptn.match(cmd[idx+1]):
					cmd[idx+1] = cmd[idx+1]+cue['slashtracktotal']

		subp.check_call(cmd)
		for o in outputs:
			os.utime(o, (atime, mtime))


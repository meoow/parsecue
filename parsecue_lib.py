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
	 u'album_artist={0}'.format(cue.get('artist', '')), 
	 u'composer={0}'.format(i.get('composer', cue.get('composer', '')))
	]
	return [ b for a in (('-metadata',x) for x in cmd if re.match(r'^[^=]+=$', x) is None ) for b in a ]+['-metadata', 'cuesheet=']

def ffmpeg(cue, encoderArgs, extname):

	if not os.path.isfile(cue['filename']):
		raise IOError("Can't not find file")

	fstat = os.stat(cue['filename'])
	atime = fstat.st_atime
	mtime = fstat.st_mtime
	
	cmds = []
	outputs = []

	for idx,i in cue['tracks'].iteritems():
		cmd = ['ffmpeg', '-y', '-hide_banner']
		output = re.sub('[/\?\'"]','_',cue.get('disc', '')+idx+' - '+i.get('title', ''))+'.'+extname.lstrip('. ')
		i = cue['tracks'][idx]
		s_n = ts1(cue, idx)
		start_dt = duration2secs(s_n[0], True)
		end_dt = duration2secs(s_n[1], True)
		dura = str((end_dt - start_dt).total_seconds())
		cmd.extend(['-ss', s_n[0], '-i', cue['filename'], '-ss', '0', '-t', dura]+encoderArgs+metadata(cue, idx)+[output])

		subp.check_call(cmd)
		os.utime(output, (atime, mtime))

def ffmpeg_mt(cue, encoderArgs, extname):

	afidx=-1
	for c,i in enumerate(encoderArgs):
		if i in ['-filter:a', '-af']:
			afidx = c+1
			break

	if not os.path.isfile(cue['filename']):
		raise IOError("Can't not find file")

	fstat = os.stat(cue['filename'])
	atime = fstat.st_atime
	mtime = fstat.st_mtime
	
	cmds = []
	outputs = []

	cmd = ['ffmpeg', '-y', '-hide_banner', '-i', cue['filename']]
	for idx,i in cue['tracks'].iteritems():
		enc = copy.copy(encoderArgs)
		output = re.sub('[/\?\'"]','_',cue.get('disc', '')+idx+' - '+i.get('title', ''))+'.'+extname.lstrip('. ')
		i = cue['tracks'][idx]
		s_n = ts1(cue, idx)
		start_dt = duration2secs(s_n[0], True).total_seconds()
		end_dt = duration2secs(s_n[1], True).total_seconds()
		atrim = 'atrim=start={0}:end={1}'.format(start_dt, end_dt)
		if afidx==-1:
			enc = ['-af', atrim]+enc
		else:
			enc[afidx] = atrim+','+enc[afidx]
		cmd.extend(enc+metadata(cue, idx))
		cmd.append(output)
		outputs.append(output)

	subp.check_call(cmd)
	for o in outputs:
		os.utime(o, (atime, mtime))

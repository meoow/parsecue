# parsecue
Splitting an audio into separate tracks via parsing CUE file

Each script, except `parsecue_lib.py` which is the shared lib, depends on different external tools,  
- afm4a requires ffmpeg and afconvert on MacOS
- flac and m4a need ffmpeg solely
- neroaac demands ffmpeg and NeroAacEnc on Linux or Windows (and MacOS if using wine).

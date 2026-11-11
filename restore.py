#!/usr/bin/env python3
"""Run from a generated backup directory, as the original XFCE user."""
from pathlib import Path
import json,subprocess,shutil,time
B=Path(__file__).resolve().parent
H=Path.home()
before=json.loads((B/'xfconf.json').read_text());managed=json.loads((B/'managed-properties.json').read_text())
def setprop(c,p,v):
 cmd=['xfconf-query','-c',c,'-p',p,'--create']
 if isinstance(v,list):cmd+=['--force-array']
 for x in v if isinstance(v,list) else [v]:
  cmd+=['-t','bool' if isinstance(x,bool) else 'int' if isinstance(x,int) else 'double' if isinstance(x,float) else 'string','-s',str(x).lower() if isinstance(x,bool) else str(x)]
 subprocess.run(cmd,check=True)
subprocess.run(['xfce4-panel','-q'],check=True);time.sleep(1)
try:
 for c,props in managed.items():
  for p in props:
   if p in before[c]:setprop(c,p,before[c][p])
   else:subprocess.run(['xfconf-query','-c',c,'-p',p,'-r'],capture_output=True)
 for rel,existed in json.loads((B/'files.json').read_text()).items():
  dest=H/rel
  if existed:shutil.copy2(B/'files'/rel,dest)
  else:dest.unlink(missing_ok=True)
finally:
 subprocess.Popen(['xfce4-panel'],start_new_session=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
print('Desktop restored. Power settings have a separate root-owned recovery script.')

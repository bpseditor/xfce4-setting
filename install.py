#!/usr/bin/env python3
"""Install an allowlisted desktop profile; never copy the source machine's home."""
import argparse,json,os,shutil,subprocess,tarfile,tempfile,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parent
HOME=Path.home()
THEME_COMMIT='4c0d7b21e201f6ed84c92207420f90648e3d2681'
FONT_COMMIT='5bb28733cec313b63fbd415b574b5ae35c8aa8b8'
def run(*args): subprocess.run(args,check=True)
def fetch(url,dest): dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(urllib.request.urlopen(url,timeout=60).read())
def main():
 p=argparse.ArgumentParser()
 p.add_argument('--dry-run',action='store_true')
 p.add_argument('--power',choices=['auto','skip'],default='auto')
 args=p.parse_args()
 model=Path('/sys/class/dmi/id/product_version')
 power=args.power=='auto' and model.exists() and model.read_text().strip()=='ThinkPad T495s'
 props=json.loads((ROOT/'config/xfconf.json').read_text())
 if args.dry_run:
  print(json.dumps({'channels':{k:len(v) for k,v in props.items()},'power_profile':'ThinkPad T495s' if power else 'desktop only','backup':'~/.local/state/xfce4-setting/backups/<timestamp>','files':'allowlisted repository payload only'},indent=2));return
 if os.geteuid()==0: raise SystemExit('Run as your logged-in XFCE user.')
 import gi
 gi.require_version('Xfconf','0')
 from gi.repository import Xfconf
 Xfconf.init()
 def setprop(channel,path,value):
  unsigned=channel=='xfce4-power-manager' and type(value) is int
  if unsigned: subprocess.run(['xfconf-query','-c',channel,'-p',path,'-r'],capture_output=True)
  cmd=['xfconf-query','-c',channel,'-p',path,'--create']
  values=value if isinstance(value,list) else [value]
  if isinstance(value,list):cmd+=['--force-array']
  for v in values:
   typ='uint' if unsigned else 'bool' if isinstance(v,bool) else 'int' if isinstance(v,int) else 'double' if isinstance(v,float) else 'string'
   cmd+=['-t',typ,'-s',str(v).lower() if isinstance(v,bool) else str(v).replace('@HOME@',str(HOME))]
  run(*cmd)
 import datetime
 backup=HOME/'.local/state/xfce4-setting/backups'/datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
 backup.mkdir(parents=True,mode=0o700)
 shutil.copy2(ROOT/'restore.py',backup/'restore.py')
 before={}
 for c in props:
  ch=Xfconf.Channel.get(c)
  before[c]={k:v if isinstance(v,(str,int,float,bool)) else list(ch.get_arrayv(k)) for k,v in ch.get_properties('/').items()}
 (backup/'xfconf.json').write_text(json.dumps(before,indent=2))
 (backup/'managed-properties.json').write_text(json.dumps(props,indent=2))
 files={}
 def save(dest):
  rel=str(dest.relative_to(HOME))
  if rel in files:return
  files[rel]=dest.exists()
  if dest.is_file():
   b=backup/'files'/rel;b.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(dest,b)
  (backup/'files.json').write_text(json.dumps(files,indent=2))
 def put(source,dest,executable=False):
  save(dest);dest.parent.mkdir(parents=True,exist_ok=True)
  shutil.copy2(source,dest);dest.chmod(0o700 if executable else 0o600)
 def text(dest,value):
  save(dest);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(value);dest.chmod(0o600)
 # Stage upstream assets before changing the session.
 with tempfile.TemporaryDirectory() as td:
  stage=Path(td);archive=stage/'theme.tar.gz'
  fetch(f'https://github.com/Bukutsu/tokyonight-xfce/archive/{THEME_COMMIT}.tar.gz',archive)
  with tarfile.open(archive) as tar:tar.extractall(stage,filter='data')
  theme=next(stage.glob('tokyonight-xfce-*/TokyoNight'))
  for f in theme.rglob('*'):
   if f.is_file():put(f,HOME/'.local/share/themes/AyuComfort'/f.relative_to(theme))
  for family,font in [('inter','Inter[opsz,wght].ttf'),('jetbrainsmono','JetBrainsMono[wght].ttf')]:
   for name in [font,'OFL.txt']:
    dest=HOME/'.local/share/fonts/desktop'/(family+'-OFL.txt' if name=='OFL.txt' else name)
    data=stage/(family+'-'+name);fetch(f'https://raw.githubusercontent.com/google/fonts/{FONT_COMMIT}/ofl/{family}/'+urllib.parse.quote(name),data);put(data,dest)
 for name in ['system-power-widget','eye-break-reminder']:put(ROOT/'bin'/name,HOME/'.local/bin'/name,True)
 put(ROOT/'config/gtk.css',HOME/'.config/gtk-3.0/gtk.css')
 put(ROOT/'config/fonts.conf',HOME/'.config/fontconfig/conf.d/60-local-fonts.conf')
 put(ROOT/'config/wallpaper.svg',HOME/'.local/share/backgrounds/ayu-comfort-horizon.svg')
 widget=HOME/'.config/system-power-widget/settings.json'
 defaults=json.loads((ROOT/'config/widget.json').read_text())
 if widget.exists():
  try:
   existing=json.loads(widget.read_text())
   if isinstance(existing,dict): defaults.update(existing)
  except (ValueError,OSError): pass
 if defaults.get('accent')=='#7dcfff': defaults['accent']='#bfbdb6'
 text(widget,json.dumps(defaults,indent=2))
 props['xfce4-panel']['/plugins/plugin-20/update-period']=max(2,min(30,int(defaults.get('panel_interval',5))))*1000
 for name,cmd,category in [('system-power-widget','system-power-widget --window','System;Monitor;'),('eye-break-reminder','eye-break-reminder','Utility;')]:
  dest=HOME/('.config/autostart' if name=='eye-break-reminder' else '.local/share/applications')/(name+'.desktop')
  text(dest,f'[Desktop Entry]\nType=Application\nName={"System & Power" if name=="system-power-widget" else "Eye break reminder"}\nExec="{HOME}/.local/bin/{name}"'+(' --window' if name=='system-power-widget' else '')+f'\nIcon=utilities-system-monitor\nTerminal=false\nOnlyShowIn=XFCE;\nCategories={category}\n')
 # Derive the GTK2/GTK3/XFWM theme from the pinned upstream assets.
 from theme import recolor_theme
 recolor_theme(HOME/'.local/share/themes/AyuComfort')
 css=HOME/'.local/share/themes/AyuComfort/gtk-3.0/gtk.css'
 text(css,css.read_text()+'\n'+(ROOT/'config/gtk.css').read_text())
 put(ROOT/'config/notify.css',HOME/'.local/share/themes/AyuComfort/xfce-notify-4.0/gtk.css')
 # Discover the new machine's monitors instead of copying the original monitor names.
 desk=Xfconf.Channel.get('xfce4-desktop').get_properties('/')
 prefixes={k.rsplit('/workspace',1)[0] for k in desk if k.startswith('/backdrop/') and '/workspace' in k}
 if not prefixes:
  gi.require_version('Gdk','3.0')
  from gi.repository import Gdk
  screen=Gdk.Screen.get_default()
  prefixes={f'/backdrop/screen0/monitor{screen.get_monitor_plug_name(i)}' for i in range(screen.get_n_monitors())}
 for prefix in prefixes:
  for i in range(4):
   for key,val in [('last-image',str(HOME/'.local/share/backgrounds/ayu-comfort-horizon.svg')),('image-style',5)]:
    path=prefix+f'/workspace{i}/'+key
    props['xfce4-desktop'][path]=val
 props['xfce4-desktop']['/backdrop/single-workspace-mode']=True
 # Explicitly suppress every installed add/delete binding.
 for k,v in Xfconf.Channel.get('xfce4-keyboard-shortcuts').get_properties('/').items():
  if v in ('add_workspace_key','del_workspace_key'):props['xfce4-keyboard-shortcuts'][k]=''
 (backup/'managed-properties.json').write_text(json.dumps(props,indent=2))
 run('xfce4-panel','-q')
 import time;time.sleep(1)
 try:
  for c,values in props.items():
   for key,val in values.items():
    if key!='/general/workspace_count':setprop(c,key,val)
  setprop('xfwm4','/general/workspace_count',4)
 finally:
  log=open(backup/'panel.log','w');subprocess.Popen(['xfce4-panel'],stdout=log,stderr=log,start_new_session=True)
 run('fc-cache','-f')
 if power:run('sudo','python3',str(ROOT/'system/apply-power.py'))
 shutil.copy2(ROOT/'restore.py',backup/'restore.py')
 print(f'Installed. Desktop rollback: python3 "{backup}/restore.py"')
 print('Log out and back in to start the session reminder.')
if __name__=='__main__':main()

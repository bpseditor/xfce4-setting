#!/usr/bin/env python3
"""Root-only, narrowly hardware-gated power setup."""
from pathlib import Path
import os,shutil,subprocess,tempfile
R=Path(__file__).resolve().parent
if os.geteuid()!=0:raise SystemExit('Root is required.')
if Path('/sys/class/dmi/id/product_version').read_text().strip()!='ThinkPad T495s':raise SystemExit('This profile requires ThinkPad T495s.')
if not Path('/sys/class/power_supply/BAT0/charge_control_end_threshold').exists():raise SystemExit('Charge thresholds are unavailable.')
subprocess.run(['xbps-install','-y','tlp'],check=True)
backup=Path(tempfile.mkdtemp(prefix='xfce-tokyo-night-',dir='/var/backups'));backup.chmod(0o700)
shutil.copy2('/etc/tlp.conf',backup/'tlp.conf')
enabled=Path('/var/service/charge-guard').is_symlink()
for path in ['/usr/local/sbin/charge-guard','/etc/sv/charge-guard']:
 p=Path(path)
 if p.is_file():shutil.copy2(p,backup/'guard-binary')
 elif p.is_dir():shutil.copytree(p,backup/'guard-service')
if enabled:subprocess.run(['sv','-w','20','down','/var/service/charge-guard'],check=True)
p=Path('/etc/tlp.conf');s=p.read_text()
import re
s=re.sub(r'\n# BEGIN xfce-tokyo-night\n.*?# END xfce-tokyo-night\n','\n',s,flags=re.S)
p.write_text(s+'\n# BEGIN xfce-tokyo-night\n'+(R/'t495s.conf').read_text()+'# END xfce-tokyo-night\n')
shutil.copy2(R/'charge-guard','/usr/local/sbin/charge-guard');os.chmod('/usr/local/sbin/charge-guard',0o755)
service=Path('/etc/sv/charge-guard');(service/'log').mkdir(parents=True,exist_ok=True)
(service/'run').write_text('#!/bin/sh\nexec 2>&1\nexec /usr/local/sbin/charge-guard\n')
(service/'log/run').write_text('#!/bin/sh\nexec svlogd -tt /var/log/charge-guard\n')
(service/'run').chmod(0o755);(service/'log/run').chmod(0o755)
logs=Path('/var/log/charge-guard');logs.mkdir(mode=0o700,exist_ok=True);(logs/'config').write_text('s65536\nn2\n')
subprocess.run(['tlp','start'],check=True)
for name in ['tlp','charge-guard']:
 p=Path('/var/service')/name
 if not p.exists():p.symlink_to('/etc/sv/'+name)
subprocess.run(['sv','up','/var/service/charge-guard'],check=True)
# Save a root-owned recovery command, including previous guard implementation.
rollback=backup/'restore.sh'
rollback.write_text('#!/bin/sh\nset -eu\nsv -w 20 down /var/service/charge-guard\n'+
 ('cp -p "'+str(backup/'guard-binary')+'" /usr/local/sbin/charge-guard\n' if (backup/'guard-binary').is_file() else '')+
 ('cp -a "'+str(backup/'guard-service')+'"/. /etc/sv/charge-guard/\n' if (backup/'guard-service').is_dir() else '')+
 'cp -p "'+str(backup/'tlp.conf')+'" /etc/tlp.conf\ntlp start\n'+
 ('sv up /var/service/charge-guard\n' if enabled else 'rm /var/service/charge-guard\n') )
rollback.chmod(0o700)
print(f'Power backup and recovery: {rollback}')

#!/usr/bin/env python3
"""Root-only, narrowly hardware-gated power setup."""
from pathlib import Path
import os,shutil,subprocess,tempfile
R=Path(__file__).resolve().parent
if os.geteuid()!=0:raise SystemExit('Root is required.')
if Path('/sys/class/dmi/id/product_version').read_text().strip()!='ThinkPad T495s':raise SystemExit('This profile requires ThinkPad T495s.')
if not Path('/sys/class/power_supply/BAT0/charge_control_end_threshold').exists():raise SystemExit('Charge thresholds are unavailable.')
subprocess.run(['xbps-install','-y','tlp'],check=True)
Path('/var/backups').mkdir(parents=True,exist_ok=True)
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
# Fixed 79/80 thresholds: do not enable the former top-up service.
service_link=Path('/var/service/charge-guard')
if service_link.is_symlink(): service_link.unlink()
subprocess.run(['tlp','start'],check=True)
p=Path('/var/service/tlp')
if not p.exists(): p.symlink_to('/etc/sv/tlp')
# Save a root-owned recovery command, including previous guard implementation.
rollback=backup/'restore.sh'
rollback.write_text('#!/bin/sh\nset -eu\n'+
 ('cp -p "'+str(backup/'guard-binary')+'" /usr/local/sbin/charge-guard\n' if (backup/'guard-binary').is_file() else '')+
 ('cp -a "'+str(backup/'guard-service')+'"/. /etc/sv/charge-guard/\n' if (backup/'guard-service').is_dir() else '')+
 'cp -p "'+str(backup/'tlp.conf')+'" /etc/tlp.conf\ntlp start\n'+
 ('ln -sfn /etc/sv/charge-guard /var/service/charge-guard\nsv up /var/service/charge-guard\n' if enabled else '') )
rollback.chmod(0o700)
print(f'Power backup and recovery: {rollback}')

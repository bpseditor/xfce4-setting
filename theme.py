"""Recolor the pinned TokyoNight base into the Ayu Comfort desktop variant."""
import re
PALETTE = {'16161e': '0d1016', '1a1b26': '151920', '24283b': '1f242c', '202332': '191e26', '292e42': '292f38', '343b58': '343c47', '3b4261': '384451', '414868': '46515e', '565f89': '6b747e', '737aa2': '7c858f', 'a9b1d6': 'a6a9ab', 'c0caf5': 'bfbdb6', '7aa2f7': '73a9c2', '7dcfff': 'd9ad72', 'bb9af7': 'c6a77b', 'f7768e': 'df8585', '9ece6a': 'a8bb85', 'e0af68': 'd9ad72', '1b1e2b': '151920'}
PALETTE.update({'6d738e':'7c858f','383e5b':'303944','181923':'13171e','0e52e4':'638fa6','eeeeee':'bfbdb6','393b53':'323b46','12121a':'10141a','181821':'151920','0e0e14':'0d1016','9ea6cb':'a6a9ab','4a80f4':'73a9c2','161720':'13171e','e00d34':'c97878','1c1d29':'191e26','709bf6':'73a9c2'})
def recolor_theme(root):
 for path in root.rglob('*'):
  if not path.is_file() or path.suffix not in ('.css','.scss','.svg','.xpm','.theme','') and path.name not in ('gtkrc','themerc'): continue
  try: text=path.read_text()
  except UnicodeDecodeError: continue
  text=re.sub(r'#([0-9a-fA-F]{6})(?![0-9a-fA-F])',lambda m:'#'+PALETTE.get(m[1].lower(),m[1]),text)
  def rgba(m):
   old=''.join(f'{int(v):02x}' for v in m.group(2,3,4))
   new=PALETTE.get(old,old)
   return m[1]+'('+', '.join(str(int(new[i:i+2],16)) for i in (0,2,4))+m[5]+')'
  text=re.sub(r'(rgba?)\(\s*(\d+),\s*(\d+),\s*(\d+)([^)]*)\)',rgba,text)
  # The upstream name remains only in licensing/source references.
  if path.name=='index.theme': text=text.replace('TokyoNight','AyuComfort')
  path.write_text(text)

 # Distinct, taller title bars keep window names separate from application text.
 style_window_frames(root/'xfwm4')

def style_window_frames(root):
 for path in root.glob('*.xpm'):
  text=path.read_text()
  inactive='inactive' in path.name
  surface='#202630' if inactive else '#303944'
  edge='#38414c' if inactive else '#596573'
  text=text.replace('#151920',surface).replace('#0d1016',surface).replace('#292f38',surface)
  lines=re.findall(r'"([^"\n]*)"',text)
  if not lines: continue
  w,h,n,cpp=map(int,lines[0].split())
  pixels=lines[1+n:]
  if h==24:
   # Equal padding above and below preserves button glyph geometry.
   pixels=pixels[:3]+[pixels[3]]*4+pixels[3:-3]+[pixels[-3]]*4+pixels[-3:]
   h=32
  palette=[line for line in lines[1:1+n] if not line.startswith('z c ')]
  if h==32 and cpp==1:
   palette.append('z c '+edge)
   transparent={line[0] for line in palette if 'None' in line}
   pixels[-1]=''.join(ch if ch in transparent else 'z' for ch in pixels[-1])
  output=[f'{w} {h} {len(palette)} {cpp}']+palette+pixels
  path.write_text('/* XPM */\nstatic char * frame[] = {\n'+',\n'.join('"'+line+'"' for line in output)+'};\n')
 path=root/'themerc'
 text=path.read_text()
 text=re.sub(r'^active_text_color=.*$', 'active_text_color=#e0d6c5',text,flags=re.M)
 text=re.sub(r'^inactive_text_color=.*$', 'inactive_text_color=#a6a9ab',text,flags=re.M)
 text=re.sub(r'^title_vertical_offset_(active|inactive)=.*$',r'title_vertical_offset_\1=0',text,flags=re.M)
 path.write_text(text)

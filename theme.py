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

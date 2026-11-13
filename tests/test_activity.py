import unittest, runpy, tempfile, sqlite3, datetime
from pathlib import Path
m=runpy.run_path(str(Path(__file__).resolve().parents[1]/'bin/activity-tracker'))
class Accounting(unittest.TestCase):
 def test_midnight_and_accumulation(self):
  db=sqlite3.connect(':memory:')
  db.execute('CREATE TABLE usage(day TEXT,app TEXT,seconds REAL,switches INTEGER,PRIMARY KEY(day,app))')
  self.addCleanup(db.close)
  midnight=datetime.datetime(2026,11,13).timestamp()
  m['record'](db,midnight-10,midnight+20,'Terminal',True)
  self.assertEqual(db.execute('SELECT seconds,switches FROM usage ORDER BY day').fetchall(),[(10,1),(20,0)])
  m['record'](db,midnight+20,midnight+25,'Terminal',False)
  self.assertEqual(db.execute('SELECT sum(seconds),sum(switches) FROM usage').fetchone(),(35,1))

class EdgeCases(unittest.TestCase):
 def setUp(self):
  self.db=sqlite3.connect(':memory:')
  self.db.execute('CREATE TABLE usage(day TEXT,app TEXT,seconds REAL,switches INTEGER,PRIMARY KEY(day,app))')
 def tearDown(self): self.db.close()
 def total(self): return self.db.execute('SELECT coalesce(sum(seconds),0) FROM usage').fetchone()[0]
 def test_active_then_pause_or_idle(self):
  m['account_sample'](self.db,100,100,'A',101,101,'A')
  m['account_sample'](self.db,101,101,'A',102,102,None)
  self.assertEqual(self.total(),1)
 def test_suspend_and_clock_jumps_not_counted(self):
  for end,mono in [(200,101),(99,101),(104,101),(110,110)]:
   m['account_sample'](self.db,100,100,'A',end,mono,'A')
  self.assertEqual(self.total(),0)
 def test_switch_counts_entry_without_charging_wrong_app(self):
  m['account_sample'](self.db,100,100,'A',101,101,'B')
  self.assertEqual(self.db.execute('SELECT app,seconds,switches FROM usage').fetchall(), [('B',0,1)])
 def test_corrupt_settings_types(self):
  from unittest.mock import patch
  for text in ['null','[]','{"paused":"false","distracting":null}','{"distracting":[3,{},"A","A"]}']:
   with tempfile.TemporaryDirectory() as td:
    config=Path(td)/'settings.json';config.write_text(text)
    with patch.dict(m['settings'].__globals__,CONFIG=config):
     result=m['settings'](); self.assertFalse(result['paused']); self.assertTrue(all(isinstance(a,str) for a in result['distracting']))

class DisplayTests(unittest.TestCase):
 def test_duration_has_seconds_and_fixed_width(self):
  self.assertEqual(m['duration'](0),'00:00:00')
  self.assertEqual(m['duration'](3661),'01:01:01')
  self.assertEqual(m['duration'](86400),'24:00:00')


class TimerTests(unittest.TestCase):
 def setUp(self):
  from unittest.mock import patch
  self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
  self.patch=patch.dict(m['database'].__globals__,DATA=Path(self.tmp.name)); self.patch.start(); self.addCleanup(self.patch.stop)
 def test_pause_resume_restart_and_complete_once(self):
  m['add_timer']('Study',60); row=m['timers']()[0]; id=row[0]
  m['timer_action'](id,'start',100)
  self.assertEqual(m['remaining_timer'](m['timers']()[0],110),50)
  m['timer_action'](id,'pause',110)
  self.assertEqual(m['remaining_timer'](m['timers']()[0],900),50)
  m['timer_action'](id,'start',900)
  self.assertEqual(m['finish_timers'](949),[])
  self.assertEqual(m['finish_timers'](950),[(id,'Study')])
  self.assertEqual(m['finish_timers'](951),[])
  m['timer_action'](id,'start',1000)
  self.assertEqual(m['remaining_timer'](m['timers']()[0],1000),60)
 def test_multiple_reset_delete_and_validation(self):
  for args in [('',60),('Study',0),('x'*61,20)]:
   with self.assertRaises(ValueError): m['add_timer'](*args)
  m['add_timer']('Study',60); m['add_timer']('Break',10)
  a,b=m['timers']()
  for row in (a,b): m['timer_action'](row[0],'start',100)
  self.assertEqual(m['finish_timers'](110),[(b[0],'Break')])
  m['timer_action'](a[0],'reset',120)
  self.assertEqual(m['timers']()[0][5],'ready')
  m['timer_action'](b[0],'delete',120)
  self.assertEqual(len(m['timers']()),1)

class CurrentAppPanelTests(unittest.TestCase):
 def test_panel_uses_current_app_even_with_running_timer(self):
  from unittest.mock import patch
  import time,json,contextlib,io
  with tempfile.TemporaryDirectory() as td:
   data=Path(td); now=time.time()
   (data/'heartbeat').write_text(str(now))
   (data/'current.json').write_text(json.dumps({'time':now,'app':'Editor'}))
   fake={'DATA':data,'rows':lambda:[('Browser',800,1),('Editor',42,2)],'settings':lambda:{'paused':False,'distracting':[]},'timers':lambda:[(1,'Study',1500,1500,now+500,'running')]}
   with patch.dict(m['panel'].__globals__,fake),contextlib.redirect_stdout(io.StringIO()) as out: m['panel']()
   label=out.getvalue().split('</txt>')[0]
   self.assertIn('Editor',label);self.assertIn('00:00:42',label);self.assertNotIn('Study',label)

if __name__=='__main__': unittest.main()

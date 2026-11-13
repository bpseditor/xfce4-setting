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

class TimerUsageTests(unittest.TestCase):
 def setUp(self):
  from unittest.mock import patch
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  p=patch.dict(m['database'].__globals__,DATA=Path(self.tmp.name))
  p.start();self.addCleanup(p.stop)
 def sample(self,start,previous,end,app,mono_start=None,mono_end=None):
  with m['contextlib'].closing(m['database']()) as db:
   a=start if mono_start is None else mono_start
   b=end if mono_end is None else mono_end
   m['account_sample'](db,start,a,previous,end,b,app)
   m['account_timer_sample'](db,start,a,previous,end,b,app)
 def test_timer_session_pause_resume_and_reset(self):
  m['add_timer']('Studying',60); tid=m['timers']()[0][0]
  m['timer_action'](tid,'start',100.25)
  self.sample(100,'Editor',101,'Editor')
  self.sample(101,'Editor',102,'Editor')
  m['timer_action'](tid,'pause',102.5)
  self.sample(102,'Editor',103,'Editor')
  self.sample(103,'Editor',104,'Editor')
  self.assertEqual(m['timer_usage_rows'](tid),[('Editor',2.25,1)])
  m['timer_action'](tid,'start',200)
  self.sample(200,'Editor',201,'Editor')
  self.assertEqual(m['timer_usage_rows'](tid),[('Editor',3.25,2)])
  m['timer_action'](tid,'reset',202)
  self.assertEqual(m['timer_usage_rows'](tid),[])
  # The global data must not be reset together with the timer session.
  with m['contextlib'].closing(m['database']()) as db:
   self.assertEqual(db.execute('SELECT SUM(seconds) FROM usage').fetchone()[0],5)
 def test_switch_no_wrong_app_charge_idle_suspend_and_completion(self):
  m['add_timer']('Study',2);tid=m['timers']()[0][0]
  m['timer_action'](tid,'start',100)
  self.sample(100,'Terminal',101,'Browser')
  self.assertEqual(m['timer_usage_rows'](tid),[('Browser',0,1)])
  self.sample(101,'Browser',102,'Browser')
  m['finish_timers'](103)
  self.sample(102,'Browser',103,'Browser')
  self.sample(103,'Browser',104,None)
  self.assertEqual(m['timer_usage_rows'](tid),[('Browser',1,1)])
  m['timer_action'](tid,'start',110)
  self.assertEqual(m['timer_usage_rows'](tid),[])
  # A monotonic/wall-clock mismatch must never accrue timer seconds.
  self.sample(110,'Browser',112,'Browser',110,111)
  self.assertEqual(sum(s for _,s,_ in m['timer_usage_rows'](tid)),0)
 def test_two_timers_are_independent_and_deleting_cascades(self):
  m['add_timer']('Study',60);m['add_timer']('Break',60)
  a,b=[r[0] for r in m['timers']()]
  m['timer_action'](a,'start',100)
  self.sample(100,'Editor',101,'Editor')
  m['timer_action'](b,'start',101)
  self.sample(101,'Editor',102,'Editor')
  m['timer_action'](a,'pause',102.5)
  self.sample(102,'Editor',103,'Editor')
  self.assertEqual(m['timer_usage_rows'](a),[('Editor',2.5,1)])
  self.assertEqual(m['timer_usage_rows'](b),[('Editor',2,1)])
  m['timer_action'](a,'delete',104)
  self.assertEqual(m['timer_usage_rows'](a),[])
  self.assertEqual(m['timer_usage_rows'](b),[('Editor',2,1)])
  with m['contextlib'].closing(m['database']()) as db:
   self.assertEqual(db.execute('SELECT COUNT(*) FROM timer_periods WHERE timer_id=?',(a,)).fetchone()[0],0)
 def test_legacy_database_upgrade_keeps_history_and_running_timer(self):
  path=Path(self.tmp.name)/'activity.sqlite3'
  with sqlite3.connect(path) as db:
   db.execute('CREATE TABLE usage(day TEXT,app TEXT,seconds REAL,switches INTEGER,PRIMARY KEY(day,app))')
   db.execute('INSERT INTO usage VALUES(?,?,?,?)',('2026-11-13','Editor',300,2))
   db.execute("CREATE TABLE timers(id INTEGER PRIMARY KEY,name TEXT,seconds INTEGER,remaining REAL,deadline REAL,state TEXT)")
   db.execute('INSERT INTO timers VALUES(1,?,?,?,?,?)',('Study',60,40,140,'running'))
  with m['contextlib'].closing(m['database']()) as db:
   self.assertEqual(db.execute('SELECT seconds FROM usage').fetchone()[0],300)
   self.assertEqual(db.execute('SELECT started,ends FROM timer_periods').fetchone(),(100,140))
  self.sample(110,'Editor',111,'Editor')
  self.assertEqual(m['timer_usage_rows'](1),[('Editor',1,1)])

class CurrentAppPanelTests(unittest.TestCase):
 def test_panel_shows_timer_and_current_app_with_session_and_daily_time(self):
  from unittest.mock import patch
  import time,json,contextlib,io
  with tempfile.TemporaryDirectory() as td:
   data=Path(td); now=time.time()
   (data/'heartbeat').write_text(str(now))
   (data/'current.json').write_text(json.dumps({'time':now,'app':'Editor'}))
   fake={'DATA':data,'rows':lambda:[('Browser',800,1),('Editor',42,2)],'settings':lambda:{'paused':False,'distracting':[]},'timers':lambda:[(1,'Study',1500,1500,now+500,'running')], 'timer_usage_rows':lambda _: [('Editor',12,1)]}
   with patch.dict(m['panel'].__globals__,fake),contextlib.redirect_stdout(io.StringIO()) as out: m['panel']()
   label=out.getvalue().split('</txt>')[0]
   self.assertIn('Study',label);self.assertIn('Editor',label)
   self.assertIn('00:12',label);self.assertNotIn('00:00:42',label)
   self.assertIn('App today: 00:00:42',out.getvalue());self.assertIn('App in session: 00:00:12',out.getvalue())

if __name__=='__main__': unittest.main()

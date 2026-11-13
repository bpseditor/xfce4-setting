import contextlib
import io
import json
from pathlib import Path
import runpy
import tempfile
import time
import unittest
from unittest.mock import patch

m=runpy.run_path(str(Path(__file__).resolve().parents[1]/'bin/activity-tracker'))

class Isolated(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.data=Path(temp.name)
        change=patch.dict(m['settings'].__globals__,DATA=self.data,CONFIG=self.data/'settings.json')
        change.start();self.addCleanup(change.stop)

class Preferences(Isolated):
    def test_round_trip_and_unrelated_preferences_survive(self):
        cfg=m['settings']();cfg.update(panel_font='Sans 14',name_length=7,paused=True,distracting=['Firefox'],idle_mode='foreground',idle_seconds=300,panel_order='app,timer,daily,distracted')
        m['save_settings'](cfg)
        self.assertEqual(m['settings'](),cfg)
        cfg['compact']=False;m['save_settings'](cfg)
        self.assertEqual(m['settings']()['distracting'],['Firefox'])
        self.assertEqual(list(self.data.iterdir()),[self.data/'settings.json'])
    def test_invalid_preferences_are_normalized(self):
        (self.data/'settings.json').write_text(json.dumps(dict(name_length=10000,idle_seconds=-1,idle_mode='bad',panel_font='',panel_order='app,app,unknown',compact='false')))
        cfg=m['settings']()
        self.assertEqual(cfg['name_length'],30);self.assertEqual(cfg['idle_seconds'],30)
        self.assertEqual(cfg['panel_order'],'app,timer,daily,distracted')
        self.assertEqual(cfg['idle_mode'],'media');self.assertTrue(cfg['compact'])

class Tracking(Isolated):
    def state(self,**changes):
        params=dict(cfg=m['settings'](),app='Firefox',idle_seconds=120,locked=False,media_playing=False);params.update(changes)
        return m['tracking_state'](**params)
    def test_foreground_video_counts_beyond_idle_threshold(self):
        self.assertEqual(self.state(),(None,'idle'))
        self.assertEqual(self.state(media_playing=True),('Firefox','media'))
        self.assertEqual(self.state(idle_seconds=59),('Firefox','active'))
    def test_lock_pause_and_no_window_override_playback(self):
        self.assertEqual(self.state(locked=True,media_playing=True),(None,'locked'))
        self.assertEqual(self.state(cfg=dict(m['settings'](),paused=True),media_playing=True),(None,'paused'))
        self.assertEqual(self.state(app=None,media_playing=True),(None,'no-window'))
    def test_modes_and_timeout(self):
        self.assertEqual(self.state(cfg=dict(m['settings'](),idle_mode='input'),media_playing=True),(None,'idle'))
        self.assertEqual(self.state(cfg=dict(m['settings'](),idle_mode='foreground')),('Firefox','foreground'))
        self.assertEqual(self.state(cfg=dict(m['settings'](),idle_seconds=300)),('Firefox','active'))
    def test_player_matching_expiry_and_pause(self):
        probe=m['MediaActivity'](None,None,None)
        probe.players={'test':(True,time.monotonic(),['firefox','Mozilla Firefox'])}
        self.assertTrue(probe.playing('firefox'));self.assertTrue(probe.playing('org.mozilla.firefox'))
        self.assertFalse(probe.playing('Terminal'));self.assertFalse(probe.playing('fire'))
        probe.players['test']=(False,time.monotonic(),['firefox']);self.assertFalse(probe.playing('firefox'))
        probe.players['test']=(True,time.monotonic()-6,['firefox']);self.assertFalse(probe.playing('firefox'))

class StopTimer(Isolated):
    def test_stop_clips_interval_preserves_stats_and_restart_resets(self):
        tid=m['add_timer']('Study',60);m['timer_action'](tid,'start',100)
        m['timer_action'](tid,'stop',101.5)
        with contextlib.closing(m['database']()) as db:
            m['account_timer_sample'](db,100,100,'Firefox',102,102,'Firefox')
        self.assertEqual(m['timers']()[0][5],'stopped')
        self.assertEqual(m['timer_usage_rows'](tid),[('Firefox',1.5,1)])
        self.assertEqual(m['remaining_timer'](m['timers']()[0],200),58.5)
        self.assertEqual(m['finish_timers'](200),[])
        m['timer_action'](tid,'start',300)
        self.assertEqual(m['timer_usage_rows'](tid),[])
        self.assertEqual(m['remaining_timer'](m['timers']()[0],300),60)
    def test_stop_from_pause_does_not_extend_session(self):
        tid=m['add_timer']('Study',60);m['timer_action'](tid,'start',100);m['timer_action'](tid,'pause',110);m['timer_action'](tid,'stop',200)
        with contextlib.closing(m['database']()) as db:
            self.assertEqual(db.execute('SELECT ends FROM timer_periods').fetchone()[0],110)
        self.assertEqual(m['timers']()[0][3],50)

class Panel(Isolated):
    def test_long_names_bounded_and_escaped_with_full_tooltip(self):
        name='Firefox <&> '+'long'*40;now=time.time()
        (self.data/'heartbeat').write_text(str(now))
        (self.data/'current.json').write_text(json.dumps(dict(app=name,time=now,reason='media')))
        tid=m['add_timer']('Long timer name <&> '+('X'*30),60);m['timer_action'](tid,'start')
        with patch.dict(m['panel'].__globals__,rows=lambda:[(name,80,1)]),contextlib.redirect_stdout(io.StringIO()) as out: m['panel']()
        result=out.getvalue();text=result.split('</txt>')[0]
        self.assertNotIn('longlong',text);self.assertIn('…',text)
        self.assertIn('Firefox &lt;&amp;&gt;',result)
        self.assertIn('Counting foreground media playback',result)
        self.assertLess(len(text),180)
    def test_paused_timer_stays_visible(self):
        tid=m['add_timer']('Study',60);m['timer_action'](tid,'start');m['timer_action'](tid,'pause')
        with contextlib.redirect_stdout(io.StringIO()) as out: m['panel']()
        self.assertIn('Ⅱ Study',out.getvalue().split('</txt>')[0])
    def test_hour_counter_keeps_seconds(self):
        self.assertEqual(m['short_duration'](3661),'1:01:01')

class DateHistory(Isolated):
    def test_specific_day_excludes_adjacent_days_and_sorts_totals(self):
        with contextlib.closing(m['database']()) as db,db:
            db.executemany('INSERT INTO usage VALUES(?,?,?,?)',[
                ('2026-11-10','Firefox',120,2),('2026-11-11','Firefox',300,3),
                ('2026-11-11','Editor',600,1),('2026-11-12','Firefox',900,4)])
        self.assertEqual(m['rows'](day='2026-11-11'),[('Editor',600,1),('Firefox',300,3)])
        self.assertEqual(m['rows'](day='2026-10-01'),[])
        with self.assertRaises(ValueError): m['rows'](day='not a date')

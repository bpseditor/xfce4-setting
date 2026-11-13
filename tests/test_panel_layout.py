import contextlib
import io
from pathlib import Path
import runpy
import unittest
from unittest.mock import patch


widget = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'bin/system-power-widget'))


class PanelLayoutTests(unittest.TestCase):
    def values(self, cfg, **changes):
        readings = dict(status='Not charging', ac=True, percent=None, power=None,
                        busy=None, used=0, mt=13.5, swap=0, swap_total=15.3,
                        cpu_temp=None, disk_percent=0, eta=None, network='')
        readings.update(changes)
        return widget['panel_metrics'](cfg, **readings)

    def test_every_metric_keeps_its_width_across_sensor_states(self):
        for compact in (False, True):
            for memory_units in ('percent', 'GiB'):
                cfg = dict(widget['DEFAULTS'], compact=compact, memory_units=memory_units)
                initial = self.values(cfg)
                for state in (
                    dict(status='Charging', percent=9, power=9.9, busy=9, used=9.9,
                         swap=9.9, cpu_temp=9, disk_percent=9, eta=9.99),
                    dict(status='Discharging', ac=False, percent=100, power=999.9,
                         busy=100, used=13.5, swap=15.3, cpu_temp=119, disk_percent=100, eta=999.99),
                    dict(status='Full', percent=100, eta=1000),
                    dict(status='Charging', power=10000, cpu_temp=-10000, eta=-1),
                ):
                    with self.subTest(compact=compact, memory_units=memory_units, state=state):
                        current = self.values(cfg, **state)
                        self.assertEqual({k: len(v) for k, v in initial.items()},
                                         {k: len(v) for k, v in current.items()})

    def test_network_reserves_both_rates_before_first_sample(self):
        network = widget['panel_network']
        for unit in ('KiB/s', 'MiB/s', 'Mbit/s'):
            initial = network('wlp1s0', 6, unit)
            for name, rx, tx in [('—', None, None), ('eth0', 0, 9.9),
                                 ('wlp1s0', 99999.9, 99999.9), ('eth0', 1000000, 1)]:
                with self.subTest(unit=unit, name=name, rx=rx):
                    current = network(name, 6, unit, rx, tx)
                    self.assertEqual(len(initial), len(current))
                    self.assertEqual(initial.index('↑'), current.index('↑'))

    def test_warning_occupies_the_same_slot_when_hidden(self):
        panel = widget['panel']
        cfg = widget['DEFAULTS']
        def sample(panel_mode=False):
            self.assertTrue(panel_mode)
            return 'CPU   9%', [], ''
        outputs = []
        with patch.dict(panel.__globals__, sample=sample, settings=lambda: cfg):
            for warning in (False, True):
                sample.warning = warning
                with contextlib.redirect_stdout(io.StringIO()) as output:
                    panel()
                outputs.append(output.getvalue())
        self.assertIn('font_family="monospace"', outputs[0])
        self.assertEqual(outputs[0].replace('alpha="1"', 'alpha="65535"')
                         .replace(cfg['accent'], cfg['warning_color']), outputs[1])

    def test_network_abbreviations_preserve_the_selected_units(self):
        network = widget['panel_network']
        self.assertIn('10.0M', network('wlp1s0', 6, 'KiB/s', 10240, 0))
        self.assertIn('10Mb', network('wlp1s0', 6, 'Mbit/s', 10, 0))
        self.assertIn('1.0Gb', network('wlp1s0', 6, 'Mbit/s', 1000, 0))
        self.assertIn('10.0G', network('wlp1s0', 6, 'MiB/s', 10240, 0))


if __name__ == '__main__':
    unittest.main()

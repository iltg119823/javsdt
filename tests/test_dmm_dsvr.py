from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from Functions.Metadata.Car import find_car_youma
from Functions.Progress.Prepare import get_suren_cars
from test_batch_control import make_config, working_directory


class DmmDsvrTests(unittest.TestCase):
    def test_reported_three_parts_share_one_identifier(self):
        for part in (1, 2, 3):
            with self.subTest(part=part):
                self.assertEqual(find_car_youma(f'twojav.com@13dsvr01936_{part}_8k.mp4', get_suren_cars()), 'DSVR-1936')

    def test_prefix_rule_is_specific_and_existing_special_ids_preserved(self):
        cases = {'13DSVR01936_1_8K.MP4': 'DSVR-1936',
                 'DSVR-1936.mp4': 'DSVR-1936',
                 'DSVR01936_2.mp4': 'DSVR-1936',
                 '20ID-020.mp4': 'ID-20020',
                 '4k688.com@DLDSS-558.mp4': 'DLDSS-558',
                 'T28-123.mp4': 'T28-123',
                 '313DSVR01936.mp4': ''}
        for filename, expected in cases.items():
            with self.subTest(filename=filename):
                self.assertEqual(find_car_youma(filename, get_suren_cars()), expected)

    def test_real_scanner_groups_and_orders_parts_numerically(self):
        with tempfile.TemporaryDirectory() as base, working_directory(base):
            handler = make_config()
            handler.rest_choose_dir(base)
            handler.rest_current_dir(base)
            files = [f'twojav.com@13dsvr01936_{part}_8k.mp4' for part in (10, 3, 2, 1)]
            for filename in files:
                Path(filename).write_bytes(b'fixture')
            handler.init_dict_subtitle_file(files)
            found = handler.get_list_jav_files(files)
            handler.count_num_and_no(found)
            self.assertEqual([file.Car for file in found], ['DSVR-1936'] * 4)
            self.assertEqual([file.Name for file in found], [f'twojav.com@13dsvr01936_{part}_8k.mp4' for part in (1, 2, 3, 10)])
            self.assertEqual([file.Episode for file in found], [1, 2, 3, 4])
            self.assertTrue(all(file.Sum_all_episodes == 4 for file in found))


if __name__ == '__main__':
    unittest.main()

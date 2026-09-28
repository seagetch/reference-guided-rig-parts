"""Regression checks for hidden RGB, partial alpha, coordinates and read-only inputs."""
from contextlib import redirect_stdout
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/reference_rgba.py'
spec = importlib.util.spec_from_file_location('reference_rgba', SCRIPT)
rgba = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rgba)


class ReferenceAlphaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source.png'
        image = Image.new('RGBA', (3, 1))
        image.putdata([(90, 40, 10, 0), (100, 50, 200, 128), (240, 245, 250, 254)])
        image.save(self.source)
        self.source_bytes = self.source.read_bytes()

    def run_cli(self, *args):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            self.assertEqual(rgba.main(list(map(str, args))), 0)
        self.assertEqual(self.source.read_bytes(), self.source_bytes)
        return json.loads(stdout.getvalue())

    def test_inspection_reports_hidden_rgb_without_writing(self):
        report = self.run_cli('inspect', self.source)
        self.assertEqual(report['source_alpha']['transparent_pixels_with_nonzero_rgb'], 1)
        self.assertEqual(report['source_alpha']['alpha_max'], 254)
        self.assertEqual(report['source_alpha']['partial_alpha_pixels'], 2)
        self.assertEqual(list(self.root.iterdir()), [self.source])

    def test_white_reference_does_not_reveal_transparent_background(self):
        target = self.root / 'white.png'
        report = self.run_cli('compose', self.source, target)
        with Image.open(target) as out:
            self.assertEqual(out.size, (3, 1))
            self.assertEqual([out.getpixel((x, 0)) for x in range(3)],
                             [(255, 255, 255), (177, 152, 227), (240, 245, 250)])
        self.assertEqual(report['source_sha256'], hashlib.sha256(self.source_bytes).hexdigest())

    def test_dark_reference_preserves_partial_coverage(self):
        target = self.root / 'dark.png'
        self.run_cli('compose', self.source, target, '--background', '#000000')
        with Image.open(target) as out:
            self.assertEqual([out.getpixel((x, 0)) for x in range(3)],
                             [(0, 0, 0), (50, 25, 100), (239, 244, 249)])

    def test_cutout_multiplies_alpha_and_keeps_visible_rgb(self):
        mask = Image.new('L', (3, 1))
        mask.putdata([255, 128, 255])
        mask_path = self.root / 'mask.png'
        mask.save(mask_path)
        target = self.root / 'part.png'
        self.run_cli('cutout', self.source, mask_path, target)
        with Image.open(target) as out:
            self.assertEqual(out.size, (3, 1))
            self.assertEqual([out.getpixel((x, 0)) for x in range(3)],
                             [(0, 0, 0, 0), (100, 50, 200, 64), (240, 245, 250, 254)])

    def test_binary_mask_excludes_pixels_without_moving_them(self):
        source = rgba.load_rgba(self.source)
        mask = Image.new('1', (3, 1))
        mask.putdata([0, 1, 0])
        out = rgba.extract_initial(source, mask)
        self.assertEqual([out.getpixel((x, 0)) for x in range(3)],
                         [(0, 0, 0, 0), (100, 50, 200, 128), (0, 0, 0, 0)])

    def test_wrong_dimensions_or_color_mask_are_rejected(self):
        source = rgba.load_rgba(self.source)
        for mask in [Image.new('L', (6, 2)), Image.new('RGBA', (3, 1))]:
            with self.assertRaises(ValueError):
                rgba.extract_initial(source, mask)

    def test_inputs_and_existing_output_cannot_be_overwritten(self):
        image = rgba.load_rgba(self.source)
        with self.assertRaises(ValueError):
            rgba.save_new_png(image, self.source, [self.source])
        target = self.root / 'existing.png'
        target.write_bytes(b'keep me')
        with self.assertRaises(FileExistsError):
            rgba.save_new_png(image, target, [self.source])
        self.assertEqual(target.read_bytes(), b'keep me')
        self.assertEqual(self.source.read_bytes(), self.source_bytes)

    def test_alpha_background_and_lossy_output_are_rejected(self):
        source = rgba.load_rgba(self.source)
        with self.assertRaises(ValueError):
            rgba.compose_reference(source, '#ffffffff')
        with self.assertRaises(ValueError):
            rgba.save_new_png(source, self.root / 'output.jpg', [self.source])


if __name__ == '__main__':
    unittest.main()

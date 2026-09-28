#!/usr/bin/env python3
"""Inspect alpha, composite a reference, or extract source pixels at 1:1.

Requires Pillow. No generation, resizing, alpha normalization, or quality scoring.
Inspection is read-only. Output commands create a new PNG and never overwrite.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

from PIL import Image, ImageColor


def load_rgba(path):
    with Image.open(path) as image:
        if getattr(image, 'n_frames', 1) != 1:
            raise ValueError('Use a single-frame source')
        return image.convert('RGBA')


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def alpha_info(image):
    histogram = image.getchannel('A').histogram()
    occupied = [i for i, count in enumerate(histogram) if count]
    channels = (channel.tobytes() for channel in image.split())
    hidden_rgb = sum(1 for r, g, b, a in zip(*channels)
                     if a == 0 and (r != 0 or g != 0 or b != 0))
    return {
        'canvas': list(image.size),
        'alpha_min': min(occupied), 'alpha_max': max(occupied),
        'transparent_pixels': histogram[0],
        'partial_alpha_pixels': sum(histogram[1:255]),
        'opaque_pixels': histogram[255],
        'transparent_pixels_with_nonzero_rgb': hidden_rgb,
        'alpha_bounds': image.getchannel('A').getbbox(),
    }


def compose_reference(source, background):
    rgb = ImageColor.getrgb(background)
    if len(rgb) != 3:
        raise ValueError('Background must be an opaque RGB color')
    canvas = Image.new('RGBA', source.size, (*rgb, 255))
    canvas.alpha_composite(source)
    return canvas.convert('RGB')


def extract_initial(source, mask):
    if mask.mode not in ('1', 'L'):
        raise ValueError('Ownership mask must have mode 1 or L')
    if source.size != mask.size:
        raise ValueError('Mask dimensions must match source; resizing is forbidden')
    original_alpha = source.getchannel('A').tobytes()
    ownership = mask.convert('L').tobytes()
    combined = bytes((a * m + 127) // 255 for a, m in zip(original_alpha, ownership))
    alpha = Image.frombytes('L', source.size, combined)
    result = source.copy()
    result.putalpha(alpha)
    # Preserve RGB wherever any source-owned coverage survives; do not expose
    # hidden background RGB by replacing the source alpha with the mask.
    result.paste((0, 0, 0, 0), mask=alpha.point(lambda a: 255 if a == 0 else 0))
    return result


def save_new_png(image, output, inputs):
    output = Path(output)
    if output.suffix.lower() != '.png':
        raise ValueError('Output must be PNG')
    if output.resolve() in {Path(p).resolve() for p in inputs}:
        raise ValueError('Output must not replace an input')
    if output.exists():
        raise FileExistsError(f'Output already exists: {output}')
    output.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation also protects against a concurrent writer.
    with output.open('xb') as stream:
        image.save(stream, format='PNG')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    inspect = commands.add_parser('inspect', help='Read alpha and source hash only')
    inspect.add_argument('source', type=Path)
    compose = commands.add_parser('compose', help='Composite onto an opaque background')
    compose.add_argument('source', type=Path)
    compose.add_argument('output', type=Path)
    compose.add_argument('--background', default='#ffffff')
    cutout = commands.add_parser('cutout', help='Initial extraction with source alpha times mask')
    cutout.add_argument('source', type=Path)
    cutout.add_argument('mask', type=Path)
    cutout.add_argument('output', type=Path)
    args = parser.parse_args(argv)
    source = load_rgba(args.source)
    report = {
        'operation': args.command,
        'source': str(args.source.resolve()),
        'source_sha256': sha256(args.source),
        'source_alpha': alpha_info(source),
        'scale': 1, 'resampling': False,
        'scope': 'Pixel/alpha operation only; NOT semantic or visual acceptance',
    }
    if args.command == 'inspect':
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    inputs = [args.source]
    if args.command == 'compose':
        result = compose_reference(source, args.background)
        report['background'] = args.background
    else:
        with Image.open(args.mask) as mask:
            if getattr(mask, 'n_frames', 1) != 1:
                raise ValueError('Use a single-frame ownership mask')
            result = extract_initial(source, mask)
        inputs.append(args.mask)
        report['mask_sha256'] = sha256(args.mask)
        report['output_alpha'] = alpha_info(result)
    save_new_png(result, args.output, inputs)
    report.update(output=str(args.output.resolve()), output_sha256=sha256(args.output),
                  output_canvas=list(result.size))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError) as exc:
        print(f'Reference RGBA error: {exc}', file=sys.stderr)
        sys.exit(1)

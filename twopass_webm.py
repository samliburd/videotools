import ffmpeg
import argparse
from pathlib import Path

AUDIO_BITRATE = 64
NUM_THREADS = 4  # Adjust based on your CPU


def parse_args():
    parser = argparse.ArgumentParser(description="Script to convert video file",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("input", type=Path, help="Path of the video file to convert")
    parser.add_argument("-s", "--scale", type=str, default='720', required=False, help="Scale")
    parser.add_argument("-t", "--target", type=int, default=4000, help="Target filesize")
    parser.add_argument("-n", "--noaudio", action="store_true", help="Remove audio")
    return parser.parse_args()


def probe_file(filename):
    return ffmpeg.probe(filename)


def get_info(probe):
    return {
        "video": next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None),
        "audio": next((stream for stream in probe['streams'] if stream['codec_type'] == 'audio'), None)
    }


def has_audio(streams, an=False):
    if not an:
        return streams["audio"] is not None
    else:
        return False


def calc_bitrate(streams, args):
    duration = float(streams["video"]['duration'])
    if has_audio(streams, args.noaudio):
        return int(args.target * 8 / duration) - AUDIO_BITRATE
    else:
        return int(args.target * 8 / duration)


def convert(args, streams, bitrate):
    input_stream = ffmpeg.input(args.input)
    video = input_stream.video.filter('scale', width='-1', height=args.scale)
    stream = [video]
    if has_audio(streams, args.noaudio):
        audio = input_stream.audio
        stream.append(audio)

    output_file = args.input.stem + ".webm"

    base_options = {
        'c:v': 'libvpx-vp9',
        'b:v': f'{bitrate}k',
        'row-mt': '1',
        'threads': NUM_THREADS  # Use multiple threads
    }

    # First pass
    first_pass_options = {
        **base_options,
        'pass': 1,
        'an': None,
        'f': 'null'
    }

    ffmpeg.output(*stream, '/dev/null', **first_pass_options).global_args('-hide_banner').run(overwrite_output=True)

    # Second pass
    second_pass_options = {**base_options, 'pass': 2}
    if has_audio(streams, args.noaudio):
        second_pass_options.update({
            'c:a': 'libopus',
            'b:a': f'{AUDIO_BITRATE}k'
        })
    else:
        second_pass_options.update({'an': None})

    ffmpeg.output(*stream, output_file, **second_pass_options).global_args('-hide_banner').run()


def main():
    args = parse_args()
    input_video = args.input
    probe = probe_file(input_video)
    streams = get_info(probe)
    bitrate = calc_bitrate(streams, args)
    print(f"Calculated bitrate: {bitrate} kbps")
    convert(args, streams, bitrate)


if __name__ == '__main__':
    main()

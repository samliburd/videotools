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
    parser.add_argument("-t", "--target", type=int, default=24500, help="Target filesize")

    return parser.parse_args()


def probe_file(filename):
    return ffmpeg.probe(filename)


def get_info(probe):
    return {
        "video": next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None),
        "audio": next((stream for stream in probe['streams'] if stream['codec_type'] == 'audio'), None)
    }


def has_audio(streams):
    return streams["audio"] is not None


def calc_bitrate(streams, target_filesize):
    duration = float(streams["video"]['duration'])
    if has_audio(streams):
        return int(target_filesize * 8 / duration) - AUDIO_BITRATE
    else:
        return int(target_filesize * 8 / duration)


def convert(args, streams, bitrate):
    input_stream = ffmpeg.input(args.input)
    video = input_stream.video.filter('scale', width='-1', height=args.scale)
    audio = input_stream.audio
    output_file = args.input.stem + "_discord" + ".mp4"

    base_options = {
        'c:v': 'libx264',
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
    ffmpeg.output(video, audio, '/dev/null', **first_pass_options).global_args('-hide_banner').run(overwrite_output=True)

    # Second pass
    second_pass_options = {**base_options, 'pass': 2}
    if has_audio(streams):
        second_pass_options.update({
            'c:a': 'aac',
            'b:a': f'{AUDIO_BITRATE}k'
        })
    else:
        second_pass_options.update({'an': None})

    ffmpeg.output(video, audio, output_file, **second_pass_options).global_args('-hide_banner').run()


def main():
    args = parse_args()
    input_video = args.input
    probe = probe_file(input_video)
    streams = get_info(probe)
    bitrate = calc_bitrate(streams, args.target)
    print(f"Calculated bitrate: {bitrate} kbps")
    convert(args, streams, bitrate)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Audio Splitter Utility
Splits audio files (e.g., M4A / AAC, MP3) into fixed-duration chunks
using PyAV with lossless stream-copying (no re-encoding) to preserve 100% quality.
"""

import argparse
import os
import sys
import av


def split_audio(
    input_path: str,
    output_dir: str = "audio_chunks",
    chunk_duration_sec: float = 180.0,
    prefix: str = "part"
):
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    os.makedirs(output_dir, exist_ok=True)

    in_container = av.open(input_path)
    if not in_container.streams.audio:
        raise ValueError("No audio streams found in the input file.")

    in_stream = in_container.streams.audio[0]
    total_dur_sec = (
        float(in_container.duration / 1_000_000)
        if in_container.duration
        else float(in_stream.duration * in_stream.time_base)
    )

    print(f"=== Audio Splitter ===")
    print(f"Input: {input_path}")
    print(f"Total Duration: {total_dur_sec:.2f}s ({int(total_dur_sec // 60):02d}:{total_dur_sec % 60:05.2f})")
    print(f"Chunk Duration: {chunk_duration_sec:.2f}s ({int(chunk_duration_sec // 60):02d}:{chunk_duration_sec % 60:05.2f})")
    print(f"Output Directory: {output_dir}")
    print("--------------------------------------------------")

    ext = os.path.splitext(input_path)[1]
    if not ext:
        ext = ".m4a"

    chunk_index = 1
    out_container = None
    out_stream = None
    chunk_start_pts = None
    current_chunk_packets = 0
    generated_files = []

    try:
        for packet in in_container.demux(in_stream):
            if packet.dts is None:
                continue

            pkt_time = float(packet.pts * packet.time_base)
            target_chunk = int(pkt_time // chunk_duration_sec) + 1

            if target_chunk != chunk_index or out_container is None:
                if out_container is not None:
                    out_container.close()
                    generated_files.append((chunk_filename, current_chunk_packets))

                chunk_index = target_chunk
                chunk_filename = os.path.join(output_dir, f"{prefix}_{chunk_index:02d}{ext}")
                out_container = av.open(chunk_filename, "w")
                out_stream = out_container.add_stream_from_template(in_stream)
                chunk_start_pts = packet.pts
                current_chunk_packets = 0

            packet.pts -= chunk_start_pts
            packet.dts -= chunk_start_pts
            packet.stream = out_stream
            out_container.mux(packet)
            current_chunk_packets += 1

        if out_container is not None:
            out_container.close()
            generated_files.append((chunk_filename, current_chunk_packets))

    finally:
        in_container.close()

    print("\nSplitting complete! Generated parts:")
    for filepath, count in generated_files:
        c = av.open(filepath)
        s = c.streams.audio[0]
        dur = (
            float(c.duration / 1_000_000)
            if c.duration
            else float(s.duration * s.time_base)
        )
        c.close()
        size_mb = os.path.getsize(filepath) / (1024 * 1024)
        print(f" - {filepath} | Duration: {int(dur // 60):02d}:{dur % 60:05.2f} ({dur:.2f}s) | Size: {size_mb:.2f} MB | Packets: {count}")


def main():
    parser = argparse.ArgumentParser(description="Split audio file into fixed-duration chunks.")
    parser.add_argument(
        "--input", "-i",
        default="videoplayback (1).m4a",
        help="Path to the input audio file (default: 'videoplayback (1).m4a')"
    )
    parser.add_argument(
        "--minutes", "-m",
        type=float,
        default=3.0,
        help="Chunk duration in minutes (default: 3.0)"
    )
    parser.add_argument(
        "--output-dir", "-o",
        default="audio_chunks",
        help="Directory to save the chunks (default: audio_chunks)"
    )
    parser.add_argument(
        "--prefix", "-p",
        default="part",
        help="File prefix for chunks (default: 'part')"
    )

    args = parser.parse_args()
    chunk_sec = args.minutes * 60.0
    split_audio(args.input, args.output_dir, chunk_sec, args.prefix)


if __name__ == "__main__":
    main()

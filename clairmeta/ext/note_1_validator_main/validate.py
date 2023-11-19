#!/usr/bin/python3

import sys
from enum import Enum
import struct
from itertools import islice
import argparse

class BadBytesException(Exception):
  def __init__(self, offset) -> None:
    self.offset = offset
    super().__init__(f"0xFFFF detected at offset {offset}")

class CodestreamException(Exception):
  def __init__(self, msg) -> None:
    super().__init__(msg)

class Marker(Enum):
  SOT = (0xFF90)
  SOD = (0xFF93, True)
  EPH = (0xFF92, True)
  SOP = (0xFF91)
  EOC = (0xFFD9, True)
  SOC = (0xFF4F, True)
  SIZ = (0xFF51)
  COD = (0xff52)
  QCD = (0xff5c)
  POC = (0xff5f)
  COM = (0xff64)
  TLM = (0xff55)
  COC = (0xff53)
  PLT = (0xff58)
  QCC = (0xff5d)
  PLM = (0xff57)
  CRG = (0xff63)

  def __new__(cls, marker, is_empty = False):
    obj = object.__new__(cls)
    obj._value_ = marker
    obj.is_empty = is_empty
    return obj

def read_byte(f, p):
  f.seek(p)
  v = f.read(1)
  if len(v) != 1:
    raise "Read error"
  return v[0]

def trigger_positions(main_header_len, tile_part_offset, tile_part_len):
  for p in range(254, main_header_len + tile_part_len, 256):
    yield (p if p < main_header_len else p - main_header_len + tile_part_offset,
           p + 1 if p < main_header_len else p + 1 - main_header_len + tile_part_offset)

def check_tile_part(f, main_header_len, tile_part_offset, tile_part_len):
  for (p1, p2) in trigger_positions(main_header_len, tile_part_offset, tile_part_len):
    if  read_byte(f, p1) == 0xFF and read_byte(f, p2) == 0xFF:
      raise BadBytesException(p1)

def validate(fn, isVerbose):
  f = open(fn, "rb")

  tile_parts_len = []
  main_header_len = 0

  while True:
    marker_bytes = f.read(2)
    if len(marker_bytes) != 2:
      break

    marker = Marker(marker_bytes[0] * 256 + marker_bytes[1])

    if marker is Marker.SOT:
      main_header_len = f.tell() - 2 # subtract the SOT marker length
      break;

    if marker.is_empty:
      continue

    size_field = f.read(2)
    if len(size_field) != 2:
      break
    segment_size = ((size_field[0] << 8) + size_field[1])

    if marker is not Marker.TLM:
      # skip over the marker segment
      f.seek(segment_size - 2, 1)
      continue

    if (isVerbose):
      print(f"Found TLM marker segment af position {hex(f.tell() - 2)}")

    if len(tile_parts_len) > 0:
      if (isVerbose):
        raise CodestreamException("Multiple TLM marker segments")

    payload = f.read(segment_size - 2)

    # stlm

    st_field = (payload[1] & 0b00110000) >> 4
    sp_field = (payload[1] & 0b01000000) >> 6

    fmt = ">"

    if st_field == 1:
      fmt += "B"
    elif st_field == 2:
      fmt += "H"

    if sp_field == 0:
      fmt += "H"
    else:
      fmt += "L"

    for entry in islice(struct.iter_unpack(fmt, payload[2:]), 3):
      tile_parts_len.append(entry[-1])

  if len(tile_parts_len) != 3:
    raise CodestreamException("Missing or incomplete TLM marker segment")

  if isVerbose:
    print(f"Tile-part lengths: {', '.join(map(str, tile_parts_len))}")

  if main_header_len <= 0:
    raise CodestreamException("Invalid Main Header length")

  if isVerbose:
    print(f"Main header length: {main_header_len}")

  # scan for the forbidden pattern

  # main_header + tile_part_1

  check_tile_part(f, main_header_len, main_header_len, tile_parts_len[0])

  # main_header + tile_part_2

  check_tile_part(f, main_header_len, main_header_len + tile_parts_len[0], tile_parts_len[1])

  # main_header + tile_part_2

  check_tile_part(f, main_header_len, main_header_len + tile_parts_len[0] + tile_parts_len[1], tile_parts_len[2])

if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="Validate codestream against Compatibility Note 1")
  parser.add_argument("-v", "--verbose", action="store_true", default=False, help="Print additional information about the codestream")
  parser.add_argument("codestream", help="Path to the codestream to be validated")
  args = parser.parse_args()

  try:
    validate(args.codestream, args.verbose)
  except Exception as e:
    sys.stderr.write(f"{e}\n")
    sys.exit(1)
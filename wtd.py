#!/usr/bin/python3

import re, argparse

def parse_args():
     parser = argparse.ArgumentParser(description='Convert logs which print macro values to the macro names')
     parser.add_argument('logfile',
                         help='Path to logfile')
     parser.add_argument('header',
                         help='path to the header file containing #defines.'
                              'Supported defines include literals and BIT()s.')
     parser.add_argument('outfile',
                         help='path to processed output file')
     try:
          return parser.parse_args()
     except argparse.ArgumentError:
          parser.print_help()
          return None

def num_to_int(num: str):
     if "x" in num:
          return int(num, 16)
     else:
          return int(num)

def genmask(left: int, right: int):
     if right > left:
          right, left = left, right
     val = 0
     for x in range(0, left-right + 1):
          val |= 1 << x
     return val << right

def genmask_mask(mask: tuple):
     return genmask(mask[0], mask[1])

"""
Parses the header file with REGEX to find macros we're interested in.
"""
def map_header(header_lines):
     header_map = {}
     """
     The part of the comment in quotes is what we are trying to match
     """
                                        # #define "blah"
     match_name = re.compile("(?<=#define\s)[a-zA-Z\d_]+(?=\s)", re.MULTILINE)
                                        # #define blah "0x123"
     match_value = re.compile("((0[xX][a-fA-F\d]+)|\d+)$", re.MULTILINE)
                                        #define blah BIT("3")
     match_value_bit = re.compile("(?<=\sBIT\()((0[xX][[a-fA-F\d]])|\d+)", re.MULTILINE)
                                        #define blah GENMASK("2", "0") <-- matches two groups
     match_value_mask = re.compile("(?<=\sGENMASK\()(\d),[\s](\d)", re.MULTILINE)
     for line in header_lines:
          name = match_name.search(line)
          value = match_value.search(line)
          bit = match_value_bit.search(line)
          mask = match_value_mask.search(line)
          if name:
               if value:
                    val = num_to_int(value.group(0))
                    header_map[name.group(0)] = {"value": val, "bits": [], "masks": []}
               elif bit:
                    header_map[list(header_map.keys())[-1]]["bits"].append({"name": name.group(0), "bit": int(bit.group(0))})
               elif mask:
                    header_map[list(header_map.keys())[-1]]["masks"].append({"name": name.group(0), "mask": (int(mask.group(1)), int(mask.group(2)))})
     return header_map

"""
Convert a value to a list of bitwise ORs like you would see in the source code
using a particular set of bits, also applies masks and shows the unshifted result, e.g.
0x08 -> "DCP_CHARGER_BIT|APSD_RESULT_STATUS_MASK=0x8"
"""
def convert_val(val, register_data):
     out_str = ""
     for bit in register_data["bits"]:
          if val & (1 << bit["bit"]):
               out_str += bit["name"] + "|"
     for mask in register_data["masks"]:
          if val & genmask_mask(mask["mask"]):
               out_str += mask["name"] + "=" \
               + hex(val & genmask_mask(mask["mask"]) >> mask["mask"][1]) + "|"
     return out_str[:-1]

"""
Iterate through a logfile, find matches of "addr = xyz" and "val = xyz"
and replace the literal values with the register defines
"""
def process_logs(logfile_lines, header):
     re_hex = "(0[xX][a-fA-F\d]+)"
     match_addr = re.compile(f"(addr\s=\s){re_hex}", re.MULTILINE)
     match_val = re.compile(f"(val\s=\s){re_hex}", re.MULTILINE)
     #[ 7292.713722] qcom,qpnp-smb2 c440000.qcom,spmi:qcom,pmi8998@2:qcom,qpnp-smb2: smblib_read(addr = 0x100d, val = 0x70)

     for i in range(len(logfile_lines)):
          line = logfile_lines[i]
          addr = match_addr.search(line)
          val = match_val.search(line)
          if not addr or not val:
               continue
          addr = addr.group(2)
          val = val.group(2)
          #print(f"{addr} = {val}")
          addr_int = num_to_int(addr)
          val_int = num_to_int(val)
          for key in header.keys():
               if header[key]["value"] == addr_int:
                    logfile_lines[i] = logfile_lines[i].replace(f"addr = {addr}", f"addr = {key}")
                    val_str = convert_val(val_int, header[key])
                    if val_str:
                         logfile_lines[i] = logfile_lines[i].replace(f"val = {val}", f"val = {val_str}")
               # elif header[key]["value"] == val_int:
               #      logfile_lines[i] = logfile_lines[i].replace(f"val = {val}", f"val = {key}")
     return logfile_lines


def main():
     args = parse_args()
     logfile_f = open(args.logfile, "r")
     logfile = [x.strip() for x in logfile_f.readlines()]
     header_f = open(args.header, "r")
     header = map_header([x.strip() for x in header_f.readlines()])
     for key in list(header.keys()):
          print(f"{key}: {header[key]}")
     fixed_log = process_logs(logfile, header)
     f = open(args.outfile, "w")
     f.write("\n".join(fixed_log))
     f.flush()
     f.close()
     print(f"\n\nDONE!\nProcessed logs written to '{args.outfile}'")

if __name__ == "__main__":
     main()

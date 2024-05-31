#! /usr/bin/env python3
'''
GameID: Identify a game using GameDB
'''

# standard imports
from datetime import datetime
from gzip import decompress as gdecompress
from gzip import open as gopen
from io import BytesIO
from os.path import abspath, expanduser, getsize, isfile
from pickle import loads as ploads
from struct import unpack
from sys import stderr
from zipfile import ZipFile
import sys
import argparse

# GameID constants
VERSION = '1.0.14'
DB_URL = 'https://github.com/niemasd/GameID/raw/main/db.pkl.gz'
DEFAULT_BUFSIZE = 1000000
FILE_MODES_GZ = {'rb', 'wb', 'rt', 'wt'}
ISO966O_UUID_TERMINATION = {ord('$'), ord('.')}
MONTH_3LET_TO_FULL = {'JAN': 'January', 'FEB': 'February', 'MAR': 'March', 'APR': 'April', 'MAY': 'May', 'JUN': 'June', 'JUL': 'July', 'AUG': 'August', 'SEP': 'September', 'OCT': 'October', 'NOV': 'November', 'DEC': 'December'}
SAFE = set('-.!0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz')

# GB/GBC constants
GB_CARTRIDGE_TYPES = {0: 'ROM', 1: 'MBC1', 2: 'MBC1 + RAM', 3: 'MBC1 + RAM + Battery', 5: 'MBC2', 6: 'MBC2 + Battery', 8: 'ROM + RAM', 9: 'ROM + RAM + Battery', 11: 'MMM01', 12: 'MMM01 + RAM', 13: 'MMM01 + RAM + Battery', 15: 'MBC3 + Timer + Battery', 16: 'MBC3 + Timer + RAM + Battery', 17: 'MBC3', 18: 'MBC3 + RAM', 19: 'MBC3 + RAM + Battery', 25: 'MBC5', 26: 'MBC5 + RAM', 27: 'MBC5 + RAM + Battery', 28: 'MBC5 + Rumble', 29: 'MBC5 + Rumble + RAM', 30: 'MBC5 + Rumble + RAM + Battery', 32: 'MBC6', 34: 'MBC7 + Sensor + Rumble + RAM + Battery', 252: 'Pocket Camera', 253: 'Bandai TAMA5', 254: 'HuC3', 255: 'HuC1 + RAM + Battery'}
GB_LICENSEE_NEW_CODES = {'00': 'None', '01': 'Nintendo R&D1', '08': 'Capcom', '13': 'Electronic Arts', '18': 'Hudson Soft', '19': 'b-ai', '20': 'kss', '22': 'pow', '24': 'PCM Complete', '25': 'san-x', '28': 'Kemco Japan', '29': 'seta', '30': 'Viacom', '31': 'Nintendo', '32': 'Bandai', '33': 'Ocean/Acclaim', '34': 'Konami', '35': 'Hector', '37': 'Taito', '38': 'Hudson', '39': 'Banpresto', '41': 'Ubi Soft', '42': 'Atlus', '44': 'Malibu', '46': 'angel', '47': 'Bullet-Proof', '49': 'irem', '50': 'Absolute', '51': 'Acclaim', '52': 'Activision', '53': 'American sammy', '54': 'Konami', '55': 'Hi tech entertainment', '56': 'LJN', '57': 'Matchbox', '58': 'Mattel', '59': 'Milton Bradley', '60': 'Titus', '61': 'Virgin', '64': 'LucasArts', '67': 'Ocean', '69': 'Electronic Arts', '70': 'Infogrames', '71': 'Interplay', '72': 'Broderbund', '73': 'sculptured', '75': 'sci', '78': 'THQ', '79': 'Accolade', '80': 'misawa', '83': 'lozc', '86': 'Tokuma Shoten Intermedia', '87': 'Tsukuda Original', '91': 'Chunsoft', '92': 'Video system', '93': 'Ocean/Acclaim', '95': 'Varie', '96': "Yonezawa/s'pal", '97': 'Kaneko', '99': 'Pack in soft', 'A4': 'Konami (Yu-Gi-Oh!)'}
GB_LICENSEE_OLD_CODES = {0: 'None', 1: 'Nintendo', 8: 'Capcom', 9: 'Hot-B', 10: 'Jaleco', 11: 'Coconuts Japan', 12: 'Elite Systems', 19: 'EA (Electronic Arts)', 24: 'Hudsonsoft', 25: 'ITC Entertainment', 26: 'Yanoman', 29: 'Japan Clary', 31: 'Virgin Interactive', 36: 'PCM Complete', 37: 'San-X', 40: 'Kotobuki Systems', 41: 'Seta', 48: 'Infogrames', 49: 'Nintendo', 50: 'Bandai', 51: None, 52: 'Konami', 53: 'HectorSoft', 56: 'Capcom', 57: 'Banpresto', 60: '.Entertainment i', 62: 'Gremlin', 65: 'Ubisoft', 66: 'Atlus', 68: 'Malibu', 70: 'Angel', 71: 'Spectrum Holoby', 73: 'Irem', 74: 'Virgin Interactive', 77: 'Malibu', 79: 'U.S. Gold', 80: 'Absolute', 81: 'Acclaim', 82: 'Activision', 83: 'American Sammy', 84: 'GameTek', 85: 'Park Place', 86: 'LJN', 87: 'Matchbox', 89: 'Milton Bradley', 90: 'Mindscape', 91: 'Romstar', 92: 'Naxat Soft', 93: 'Tradewest', 96: 'Titus', 97: 'Virgin Interactive', 103: 'Ocean Interactive', 105: 'EA (Electronic Arts)', 110: 'Elite Systems', 111: 'Electro Brain', 112: 'Infogrames', 113: 'Interplay', 114: 'Broderbund', 115: 'Sculptered Soft', 117: 'The Sales Curve', 120: 't.hq', 121: 'Accolade', 122: 'Triffix Entertainment', 124: 'Microprose', 127: 'Kemco', 128: 'Misawa Entertainment', 131: 'Lozc', 134: 'Tokuma Shoten Intermedia', 139: 'Bullet-Proof Software', 140: 'Vic Tokai', 142: 'Ape', 143: "I'Max", 145: 'Chunsoft Co.', 146: 'Video System', 147: 'Tsubaraya Productions Co.', 149: 'Varie Corporation', 150: "Yonezawa/S'Pal", 151: 'Kaneko', 153: 'Arc', 154: 'Nihon Bussan', 155: 'Tecmo', 156: 'Imagineer', 157: 'Banpresto', 159: 'Nova', 161: 'Hori Electric', 162: 'Bandai', 164: 'Konami', 166: 'Kawada', 167: 'Takara', 169: 'Technos Japan', 170: 'Broderbund', 172: 'Toei Animation', 173: 'Toho', 175: 'Namco', 176: 'acclaim', 177: 'ASCII or Nexsoft', 178: 'Bandai', 180: 'Square Enix', 182: 'HAL Laboratory', 183: 'SNK', 185: 'Pony Canyon', 186: 'Culture Brain', 187: 'Sunsoft', 189: 'Sony Imagesoft', 191: 'Sammy', 192: 'Taito', 194: 'Kemco', 195: 'Squaresoft', 196: 'Tokuma Shoten Intermedia', 197: 'Data East', 198: 'Tonkinhouse', 200: 'Koei', 201: 'UFL', 202: 'Ultra', 203: 'Vap', 204: 'Use Corporation', 205: 'Meldac', 206: '.Pony Canyon or', 207: 'Angel', 208: 'Taito', 209: 'Sofel', 210: 'Quest', 211: 'Sigma Enterprises', 212: 'ASK Kodansha Co.', 214: 'Naxat Soft', 215: 'Copya System', 217: 'Banpresto', 218: 'Tomy', 219: 'LJN', 221: 'NCS', 222: 'Human', 223: 'Altron', 224: 'Jaleco', 225: 'Towa Chiki', 226: 'Yutaka', 227: 'Varie', 229: 'Epcoh', 231: 'Athena', 232: 'Asmik ACE Entertainment', 233: 'Natsume', 234: 'King Records', 235: 'Atlus', 236: 'Epic/Sony Records', 238: 'IGS', 240: 'A Wave', 243: 'Extreme Entertainment', 255: 'LJN'}
GB_NINTENDO_LOGO = bytes([0xCE, 0xED, 0x66, 0x66, 0xCC, 0x0D, 0x00, 0x0B, 0x03, 0x73, 0x00, 0x83, 0x00, 0x0C, 0x00, 0x0D, 0x00, 0x08, 0x11, 0x1F, 0x88, 0x89, 0x00, 0x0E, 0xDC, 0xCC, 0x6E, 0xE6, 0xDD, 0xDD, 0xD9, 0x99, 0xBB, 0xBB, 0x67, 0x63, 0x6E, 0x0E, 0xEC, 0xCC, 0xDD, 0xDC, 0x99, 0x9F, 0xBB, 0xB9, 0x33, 0x3E])
GB_RAM_SIZE_BANKS = {0: (0, 0), 1: (2048, 1), 2: (8192, 1), 3: (32768, 4), 4: (131072, 16), 5: (65536, 8)}
GB_ROM_SIZE_BANKS = {0: (32768, 2), 1: (65536, 4), 2: (131072, 8), 3: (262144, 16), 4: (524288, 32), 5: (1048576, 64), 6: (2097152, 128), 7: (4194304, 256), 8: (8388608, 512), 82: (1179648, 72), 83: (1310720, 80), 84: (1572864, 96)}

# GBA constants
GBA_NINTENDO_LOGO = bytes([0x24, 0xFF, 0xAE, 0x51, 0x69, 0x9A, 0xA2, 0x21, 0x3D, 0x84, 0x82, 0x0A, 0x84, 0xE4, 0x09, 0xAD, 0x11, 0x24, 0x8B, 0x98, 0xC0, 0x81, 0x7F, 0x21, 0xA3, 0x52, 0xBE, 0x19, 0x93, 0x09, 0xCE, 0x20, 0x10, 0x46, 0x4A, 0x4A, 0xF8, 0x27, 0x31, 0xEC, 0x58, 0xC7, 0xE8, 0x33, 0x82, 0xE3, 0xCE, 0xBF, 0x85, 0xF4, 0xDF, 0x94, 0xCE, 0x4B, 0x09, 0xC1, 0x94, 0x56, 0x8A, 0xC0, 0x13, 0x72, 0xA7, 0xFC, 0x9F, 0x84, 0x4D, 0x73, 0xA3, 0xCA, 0x9A, 0x61, 0x58, 0x97, 0xA3, 0x27, 0xFC, 0x03, 0x98, 0x76, 0x23, 0x1D, 0xC7, 0x61, 0x03, 0x04, 0xAE, 0x56, 0xBF, 0x38, 0x84, 0x00, 0x40, 0xA7, 0x0E, 0xFD, 0xFF, 0x52, 0xFE, 0x03, 0x6F, 0x95, 0x30, 0xF1, 0x97, 0xFB, 0xC0, 0x85, 0x60, 0xD6, 0x80, 0x25, 0xA9, 0x63, 0xBE, 0x03, 0x01, 0x4E, 0x38, 0xE2, 0xF9, 0xA2, 0x34, 0xFF, 0xBB, 0x3E, 0x03, 0x44, 0x78, 0x00, 0x90, 0xCB, 0x88, 0x11, 0x3A, 0x94, 0x65, 0xC0, 0x7C, 0x63, 0x87, 0xF0, 0x3C, 0xAF, 0xD6, 0x25, 0xE4, 0x8B, 0x38, 0x0A, 0xAC, 0x72, 0x21, 0xD4, 0xF8, 0x07])

# Genesis constants
GENESIS_DEVICE_SUPPORT = {'J': '3-button Controller', '6': '6-button Controller', '0': 'Master System Controller', 'A': 'Analog Joystick', '4': 'Multitap', 'G': 'Lightgun', 'L': 'Activator', 'M': 'Mouse', 'B': 'Trackball', 'T': 'Tablet', 'V': 'Paddle', 'K': 'Keyboard or Keypad', 'R': 'RS-232', 'P': 'Printer', 'C': 'CD-ROM (Sega CD)', 'F': 'Floppy Drive', 'D': 'Download'}
GENESIS_REGION_SUPPORT = {'J': 'Japan', 'U': 'Americas', 'E': 'Europe'}
GENESIS_SOFTWARE_TYPES = {'GM': 'Game', 'AI': 'Aid', 'OS': 'Boot ROM (TMSS)', 'BR': 'Boot ROM (Sega CD)'}
GENESIS_SYSTEM_TYPES = {"SEGA MEGA DRIVE", "SEGA GENESIS", "SEGA 32X", "SEGA EVERDRIVE", "SEGA SSF", "SEGA MEGAWIFI", "SEGA PICO", "SEGA TERA68K", "SEGA TERA286"}

# N64 constants
N64_FIRST_WORD = b'\x80\x37\x12\x40'

# PSX constants
PSX_HEADER = b'\x00\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\x00'

# SNES constants
SNES_LOROM_HEADER_START = 0x7FC0
SNES_HIROM_HEADER_START = 0xFFC0

# print a log message
def print_log(message='', end='\n', file=stderr):
    print(message, end=end, file=file); file.flush()

# print an error message and exit
def error(message, exitcode=1):
    print(message, file=stderr); exit(exitcode)

# check if a file exists and throw an error if it doesn't
def check_exists(fn):
    if not isfile(fn):
        error("File not found: %s" % fn)

# check if a file doesn't exist and throw an error if it does
def check_not_exists(fn):
    if isfile(fn):
        error("File exists: %s" % fn)

# open an output text file for writing (automatically handle gzip)
def open_file(fn, mode='rt', bufsize=DEFAULT_BUFSIZE):
    ext = fn.split('.')[-1].strip().lower()

    # standard output/input
    if fn == 'stdout':
        from sys import stdout as f
    elif fn == 'stdin':
        from sys import stdin as f

    # GZIP files
    elif ext == 'gz':
        if mode not in FILE_MODES_GZ:
            error("Invalid gzip file mode: %s" % mode)
        elif 'r' in mode:
            f = gopen(fn, mode)
        elif 'w' in mode:
            f = gopen(fn, mode, compresslevel=9)
        else:
            error("Invalid gzip file mode: %s" % mode)

    # ZIP files
    elif ext == 'zip':
        if 'r' not in mode or 'w' in mode:
            error("Only read mode is supported for gzip files")
        z = ZipFile(fn, 'r'); names = z.namelist()
        if len(names) != 1:
            error("More than 1 file in zip: %s" % fn)
        return z.open(names[0])

    # Regular files
    else:
        f = open(fn, mode, buffering=bufsize)
    return f

# helper class to serve as a file pointer for pycdlib (to support GZIP, weird PSX discs, etc.)
class ISO9660FP:
    # constrctor
    def __init__(self, fn, mode, start_offset=0, bufsize=DEFAULT_BUFSIZE):
        self.f = open_file(fn, mode, bufsize=bufsize)
        self.mode = mode; self.start_offset = start_offset

    # seek to offset
    def seek(self, offset, from_what=0):
        if from_what == 0: # reference point is start of file
            offset += self.start_offset
        self.f.seek(offset, from_what)

    # tell current offset
    def tell(self):
        return self.f.tell() - self.start_offset

    # read data
    def read(self, read_size):
        return self.f.read(read_size)

# get args from user interactively
def get_args_interactive(argv):
    # set things up
    print_log("=== GameID v%s ===" % VERSION)
    arg_input = None; arg_console = None

    # get game filename (--input)
    while arg_input is None:
        print_log("Enter game title (no quotes): ", end='')
        arg_input = input().strip()
        if not isfile(arg_input):
            print_log("ERROR: File not found: %s\n" % arg_input); arg_input = None
    argv += ['--input', arg_input]

    # get console (--console)
    while arg_console is None:
        print_log("Enter console (options: %s): " % ', '.join(sorted(IDENTIFY.keys())), end='')
        arg_console = input().replace('"','').replace("'",'').strip()
        if arg_console not in IDENTIFY:
            print_log("ERROR: Invalid console: %s\n" % arg_console); arg_console = None
    argv += ['--console', arg_console]

# parse user arguments
def parse_args():
    # if --version, just print version and exit
    if '--version' in sys.argv:
        print("GameID v%s" % VERSION); exit()

    # run argparse
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-i', '--input', required=True, type=str, help="Input Game File")
    parser.add_argument('-c', '--console', required=True, type=str, help="Console (options: %s)" % ', '.join(sorted(IDENTIFY.keys())))
    parser.add_argument('-d', '--database', required=False, type=str, default=None, help="GameID Database (db.pkl.gz)")
    parser.add_argument('-o', '--output', required=False, type=str, default='stdout', help="Output File")
    parser.add_argument('--delimiter', required=False, type=str, default='\t', help="Delimiter")
    parser.add_argument('--prefer_gamedb', action="store_true", help="Prefer Metadata in GameDB (rather than metadata loaded from game)")
    parser.add_argument('--version', action="store_true", help="Print GameID Version (%s)" % VERSION)
    args = parser.parse_args()

    # check console
    check_console(args.console)

    # check input game file
    args.input = abspath(expanduser(args.input))
    check_exists(args.input)

    # check input database file
    if args.database is not None:
        args.database = abspath(expanduser(args.database))
        check_exists(args.database)

    # check output file
    if args.output != 'stdout':
        check_not_exists(args.output)

    # all good, so return args
    return args

# load GameID database
def load_db(fn, bufsize=DEFAULT_BUFSIZE):
    if fn is None:
        from urllib.request import urlopen; data = gdecompress(urlopen(DB_URL).read())
    else:
        f = open_file(fn, 'rb', bufsize=bufsize); data = f.read(); f.close()
    return ploads(data)

# identify PSP game
def identify_psp(fn, db, prefer_gamedb=False):
    # open PSP ISO
    try:
        from pycdlib import PyCdlib
    except:
        error("Unable to import pycdlib. Install with: pip install pycdlib")
    iso = PyCdlib(); iso.open_fp(ISO9660FP(fn,'rb')); data = BytesIO(); iso.get_file_from_iso_fp(data, iso_path='/UMD_DATA.BIN')

    # read serial
    serial = ""
    for v in data.getvalue():
        if v == ord('|'):
            break
        serial += chr(v)
    serial = serial.strip()

    # identify game
    if serial in db['PSP']:
        return db['PSP'][serial]

# identify PSX/PS2 game
def identify_psx_ps2(fn, db, console, prefer_gamedb=False):
    # set things up
    iso = ISO9660(fn, console); out = None; serial = None

    # try to find file in root directory with name SXXX_XXX.XX
    root_fns = [root_fn.lstrip('/') for root_fn, file_lba, file_len in iso.get_filenames(only_root_dir=True)]
    for prefix in db['GAMEID'][console]['ID_PREFIXES']:
        for root_fn in root_fns:
            if root_fn.startswith(prefix):
                serial = root_fn.replace('.','').replace('-','_')
                if serial not in db[console] and len(serial) > len(prefix): # might have a different delimiter than '-' or '_' (e.g. DQ7 is 'SLUSP012.06)
                    serial = serial[:len(prefix)] + '_' + serial[len(prefix)+1:]
                if serial in db[console]:
                    out = db[console][serial]; break
        if serial is not None:
            break

    # failed to find serial based on file, so try volume ID
    if out is None:
        volume_ID = iso.get_volume_ID()
        if isinstance(volume_ID, str):
            serial = volume_ID.replace('-','_'); num_underscore = serial.count('_')
            if num_underscore == 2:
                serial = '_'.join(serial.split('_')[:2])
            if serial in db[console]:
                out = db[console][serial]

    # finalize output and return
    if out is None:
        error("%s game not found (%s): %s\t%s" % (console, volume_ID, fn, root_fns))
    else:
        out['ID'] = serial.replace('_','-')
        for k,v in [('uuid',iso.get_uuid()), ('volume_ID',iso.get_volume_ID())]:
            if (k not in out) or (not prefer_gamedb):
                out[k] = v
        return out

# identify PSX game
def identify_psx(fn, db, prefer_gamedb=False):
    return identify_psx_ps2(fn, db, 'PSX', prefer_gamedb=prefer_gamedb)

# identify PS2 game
def identify_ps2(fn, db, prefer_gamedb=False):
    return identify_psx_ps2(fn, db, 'PS2', prefer_gamedb=prefer_gamedb)

# identify GB/GBC game
def identify_gb_gbc(fn, db, prefer_gamedb=False):
    # parse GB/GBC ROM header: https://github.com/niemasd/GameDB-GB/wiki#memory-map
    f = open_file(fn, mode='rb'); data = f.read(); f.close()
    if data[0x0104 : 0x0134] != GB_NINTENDO_LOGO:
        pass # error("Invalid GB/GBC ROM (Nintendo logo mismatch): %s" % fn)
    title = data[0x0134 : 0x013F]; manufacturer_code = data[0x013F : 0x0143]; cgb_flag = data[0x0143]

    # parse CGB flag (whether or not GameBoy Color features are supported)
    if cgb_flag == 0x80:
        cgb_mode = "GBC (supports GB)"
    elif cgb_flag == 0xC0:
        cgb_mode = "GBC only"
    elif (cgb_flag & 0b00001100) != 0:
        cgb_mode = "PGB"
    else: # probably old GB game where this byte is part of title
        cgb_mode = "GB"

    # parse manufacturer code (and potentially expand title if there is none)
    if sum(1 for v in manufacturer_code if ord('A') <= v <= ord('Z')) == 4:
        manufacturer_code = manufacturer_code.decode()
    else:
        title = data[0x0134 : 0x0144]; manufacturer_code = None
    title = bytes([v if ord(' ') <= v <= ord('~') else ord(' ') for v in title]).decode().strip()

    # parse Super GameBoy support
    sgb_support = (data[0x0146] == 0x03)

    # parse cartridge type
    if data[0x0147] in GB_CARTRIDGE_TYPES:
        cartridge_type = GB_CARTRIDGE_TYPES[data[0x0147]]
    else:
        cartridge_type = "Unknown"

    # parse ROM size (bytes) and number of banks
    if data[0x0148] in GB_ROM_SIZE_BANKS:
        rom_size, rom_banks = GB_ROM_SIZE_BANKS[data[0x0148]]
    else:
        rom_size = "Unknown"; rom_banks = "Unknown"

    # parse RAM size (bytes) and number of banks
    if data[0x0149] in GB_RAM_SIZE_BANKS:
        ram_size, ram_banks = GB_RAM_SIZE_BANKS[data[0x0149]]
    else:
        ram_size = "Unknown"; ram_banks = "Unknown"

    # parse licensee code
    if data[0x014B] == 0x33: # new licensee code
        try:
            licensee = GB_LICENSEE_NEW_CODES[data[0x0144 : 0x0146].decode()]
        except: # new licensee code not found
            licensee = "Unknown"
    elif data[0x014B] in GB_LICENSEE_OLD_CODES: # old licensee code
        licensee = GB_LICENSEE_OLD_CODES[data[0x014B]]
    else: # old licensee code not found
        licensee = "Unknown"

    # parse ROM version
    rom_version = data[0x014C]

    # parse expected checksums
    header_checksum_expected = data[0x014D]
    global_checksum_expected = unpack('>H', data[0x014E:0x0150])[0]

    # calculate actual checksums
    header_checksum_actual = 256
    for v in data[0x0134 : 0x014D]:
        header_checksum_actual -= (v+1)
        while header_checksum_actual < 0:
            header_checksum_actual += 256
    global_checksum_actual = sum(v for i,v in enumerate(data) if i not in {0x014E, 0x014F}) % 65536

    # identify game
    gamedb_ID = (title, global_checksum_expected)
    out = {
        'internal_title': title,
        'cgb_mode': cgb_mode,
        'sgb_support': sgb_support,
        'cartridge_type': cartridge_type,
        'rom_size': rom_size,
        'rom_banks': rom_banks,
        'ram_size': ram_size,
        'ram_banks': ram_banks,
        'licensee': licensee,
        'rom_version': rom_version,
        'header_checksum_expected': '0x%s' % hex(header_checksum_expected)[2:].zfill(2),
        'header_checksum_actual': '0x%s' % hex(header_checksum_actual)[2:].zfill(2),
        'global_checksum_expected': '0x%s' % hex(global_checksum_expected)[2:].zfill(4),
        'global_checksum_actual': '0x%s' % hex(global_checksum_actual)[2:].zfill(4),
    }
    if manufacturer_code is not None:
        out['manufacturer_code'] = manufacturer_code
    if gamedb_ID in db['GB_GBC']:
        gamedb_entry = db['GB_GBC'][gamedb_ID]
        for k,v in gamedb_entry.items():
            if (k not in out) or prefer_gamedb:
                out[k] = v
    else:
        out['title'] = out['internal_title'] # 'title' and 'internal_title' will be the same if game not found in GameDB
    return out

# identify GBA game
def identify_gba(fn, db, prefer_gamedb=False):
    # parse GBA ROM header: http://problemkaputt.de/gbatek-gba-cartridge-header.htm
    f = open_file(fn, mode='rb'); data = f.read(192); f.close()
    if data[0x04 : 0xA0] != GBA_NINTENDO_LOGO:
        pass # error("Invalid GBA ROM (Nintendo logo mismatch): %s" % fn)
    title = ''.join(chr(v) for v in data[0xA0 : 0xAC] if ord(' ') <= v <= ord('~')).strip()
    game_code = ''.join(chr(v) for v in data[0xAC : 0xB0] if ord(' ') <= v <= ord('~')).strip()
    maker_code = ''.join(chr(v) for v in data[0xB0 : 0xB2] if ord(' ') <= v <= ord('~')).strip()
    main_unit_code = data[0xB3]
    device_type = data[0xB4]
    software_version = data[0xBC]

    # identify game
    out = {
        'ID': game_code,
        'internal_title': title,
        'maker_code': maker_code,
        'main_unit_code': '0x%s' % hex(main_unit_code)[2:].zfill(2),
        'device_type': '0x%s' % hex(device_type)[2:].zfill(2),
        'software_version': software_version,
    }
    if game_code in db['GBA']:
        gamedb_entry = db['GBA'][game_code]
        for k,v in gamedb_entry.items():
            if (k not in out) or prefer_gamedb:
                out[k] = v
    else:
        out['title'] = out['internal_title'] # 'title' and 'internal_title' will be the same if game not found in GameDB
    return out

# identify GC game
def identify_gc(fn, db, prefer_gamedb=False):
    # open GC ISO
    try:
        from gciso import IsoFile as GCIsoFile
    except:
        error("Unable to import gciso. Install with: pip install git+https://github.com/pfirsich/gciso.git")
    iso = GCIsoFile(fn)

    # build initial output: https://gciso.readthedocs.io/en/latest/#gciso.IsoFile
    serial = iso.gameCode.decode()
    out = {
        'internal_title': iso.gameName.decode(),
        'ID': serial,
        'maker_code': iso.makerCode.decode(),
        'disk_ID': iso.diskId,
        'version': iso.version,
        'dol_offset': iso.dolOffset,
        'dol_size': iso.dolSize,
        'fst_offset': iso.fstOffset,
        'fst_size': iso.fstSize,
        'max_fst_size': iso.maxFstSize,
        'num_fst_entries': iso.numFstEntries,
        'string_table_offset': iso.stringTableOffset,
        'apploader_date': iso.apploaderDate.decode().replace('/','-'),
        'apploader_entry_point': iso.apploaderEntryPoint,
        'apploader_code_size': iso.apploaderCodeSize,
        'apploader_trailer_size': iso.apploaderTrailerSize,
    }

    # identify game
    if serial in db['GC']:
        gamedb_entry = db['GC'][serial]
        for k,v in gamedb_entry.items():
            if (k not in out) or prefer_gamedb:
                out[k] = v
    else:
        out['title'] = out['internal_title'] # 'title' and 'internal_title' will be the same if game not found in GameDB
    return out

# helper function convert N64 data between little-endian and big-endian
def n64_convert_endianness(data):
    if len(data) % 2 != 0:
        error("Can only convert even-length data")
    out = bytearray(len(data))
    for i in range(0, len(data), 2):
        out[i] = data[i+1]; out[i+1] = data[i]
    return out

# identify N64 game
def identify_n64(fn, db, prefer_gamedb=False):
    f = open_file(fn, mode='rb'); header = f.read(0x40) # stop before "Boot code/strap"

    # determine endianness from first word: https://en64.shoutwiki.com/wiki/ROM
    first_word_data = header[0 : 4]
    if n64_convert_endianness(first_word_data) == N64_FIRST_WORD: # little-endian, so need to convert to big-endian
        header = n64_convert_endianness(header)
    elif first_word_data != N64_FIRST_WORD: # doesn't match either endianness
        error("Invalid N64 ROM: %s" % fn)

    # parse N64 ROM header: https://en64.shoutwiki.com/wiki/ROM#Cartridge_ROM_Header
    cartridge_ID = header[0x3c : 0x3e]
    country_code, version = header[0x3e : 0x40]

    # identify game
    try:
        serial = '%s%s%s' % (chr(cartridge_ID[0]), chr(cartridge_ID[1]), chr(country_code))
    except:
        error("Invalid N64 ROM (%s %s): %s" % (cartridge_ID, country_code, fn))
    if serial in db['N64']:
        out = db['N64'][serial]
        out['ID'] = serial
        if not prefer_gamedb:
            internal_name = header[0x20 : 0x34]
            try:
                out['title'] = internal_name.decode().strip()
            except:
                out['title'] = internal_name
        f.close()
        return out
    f.close(); error("N64 game not found (%s %s): %s" % (cartridge_ID, country_code, fn))

# identify SNES game
def identify_snes(fn, db, prefer_gamedb=False):
    # load ROM and remove optional 512-byte header: https://snes.nesdev.org/wiki/ROM_file_formats#Detecting_Headered_ROM
    f = open_file(fn, mode='rb'); data = f.read(); f.close()
    if (len(data) % 1024) == 512:
        data = data[512:]

    # find header start: https://github.com/JonnyWalker/PySNES/blob/13ed51843ef391426ebecae643f955da232dcf33/venv/pysnes/cartrige.py#L71-L83
    checksum = None; header_start =  None
    try:
        for start_addr in [SNES_LOROM_HEADER_START, SNES_HIROM_HEADER_START]:
            # https://github.com/JonnyWalker/PySNES/blob/13ed51843ef391426ebecae643f955da232dcf33/venv/pysnes/cartrige.py#L85-L99
            cs1 = hex(data[start_addr + 30])[2:]
            cs1 = (2 - len(cs1)) * "0" + cs1
            cs2 = hex(data[start_addr + 31])[2:]
            cs2 = (2 - len(cs2)) * "0" + cs2
            checksum = cs2 + cs1
            csc1 = hex(data[start_addr + 28])[2:]
            csc1 = (2 - len(csc1)) * "0" + csc1
            csc2 = hex(data[start_addr + 29])[2:]
            csc2 = (2 - len(csc2)) * "0" + csc2
            checksum_complement = csc2 + csc1
            if (int(checksum, 16) + int(checksum_complement, 16) == 65535):
                header_start = start_addr; break
    except:
        pass
    if header_start is None:
        error("Invalid SNES ROM: %s" % fn)

    # parse SNES ROM header: https://snes.nesdev.org/wiki/ROM_header#Cartridge_header
    header = data[header_start:]
    internal_name = header[0 : 21]; internal_name_hex_string = '0x%s' % ''.join(hex(v)[2:].zfill(2) for v in internal_name)
    developer_ID = header[26]
    rom_version = header[27]

    # https://en.wikibooks.org/wiki/Super_NES_Programming/SNES_memory_map#How_do_I_recognize_the_ROM_type?
    if (header[21] & 0b00010000) == 0:
        fast_slow_rom = 'SlowROM'
    else:
        fast_slow_rom = 'FastROM'
    if (header[21] & 0b00000001) == 0:
        rom_type = "LoROM"
    else:
        rom_type = "HiROM"
    if (header[21] & 0b00000100) != 0:
        rom_type = "Ex%s" % rom_type

    # https://snes.nesdev.org/wiki/ROM_header#$FFD6
    hardware = None
    if header[22] <= 2: # [0x00, 0x01, 0x02]
        hardware = ["ROM", "ROM + RAM", "ROM + RAM + Battery"][header[22]]
    else:
        tmp = hex(header[22]).lower() # $FFD6
        coprocessor = None
        if '3' <= tmp[-1] <= '6': # [0x?3, 0x?4, 0x?5, 0x?6]
            hardware = ["ROM + Coprocessor", "ROM + Coprocessor + RAM", "ROM + Coprocessor + RAM + Battery", "ROM + Coprocessor + Battery"][int(tmp[-1])-3]
        if '0' <= tmp[-2] <= '5': # [0x0?, 0x1?, 0x2?, 0x3?, 0x4?, 0x5?]
            coprocessor = ["DSP", "GSU / SuperFX", "OBC1", "SA-1", "S-DD1", "S-RTC"][int(tmp[-2])]
        elif tmp[-2] == 'e': # 0xe?
            coprocessor = "Super Game Boy / Satellaview"
        elif tmp[-2] == 'f': # 0xf?
            tmp = hex(data[header_start-1]) # $FFBF
            if (tmp[-2] == '0') and ('0' <= tmp[-1] <= '3'): # [0x00, 0x01, 0x02, 0x03]
                coprocessor = ["SPC7110", "ST010 / ST011", "ST018", "CX4"][int(tmp[-1])]
        if hardware is not None and coprocessor is not None:
            hardware = hardware.replace(" + Coprocessor", " + Coprocessor (%s)" % coprocessor)

    # identify game
    gamedb_ID = (developer_ID, internal_name_hex_string, rom_version, int(checksum,16))
    out = {
        'internal_title': internal_name_hex_string,
        'fast_slow_rom': fast_slow_rom,
        'rom_type': rom_type,
        'developer_ID': '0x%s' % hex(developer_ID)[2:].zfill(2),
        'rom_version': rom_version,
        'checksum': '0x%s' % checksum.zfill(4),
    }
    if hardware is not None:
        out['hardware'] = hardware
    if gamedb_ID in db['SNES']:
        gamedb_entry = db['SNES'][gamedb_ID]
        for k,v in gamedb_entry.items():
            if (k not in out) or prefer_gamedb:
                out[k] = v
    else:
        out['title'] = ''.join(chr(v) if ord(' ') <= v <= ord('~') else ' ' for v in internal_name).strip()
    return out

# identify Genesis game
def identify_genesis(fn, db, prefer_gamedb=False):
    # parse Genesis ROM header: https://plutiedev.com/rom-header
    f = open_file(fn, mode='rb'); data = f.read(); f.close()

    # system type
    try:
        system_type = data[0x100 : 0x110].decode().strip()
    except:
        system_type = None
    if system_type not in GENESIS_SYSTEM_TYPES:
        error("Invalid Genesis ROM: %s" % fn)

    # publisher
    publisher = data[0x113 : 0x117]
    try:
        publisher = publisher.decode().strip()
    except:
        pass

    # release year
    release_year = data[0x118 : 0x11C]
    try:
        release_year = int(release_year.decode())
    except:
        pass

    # release month
    release_month = data[0x11D : 0x120]
    try:
        release_month = release_month.decode().strip()
    except:
        pass
    if release_month in MONTH_3LET_TO_FULL:
        release_month = MONTH_3LET_TO_FULL[release_month]

    # domestic title
    title_domestic = data[0x120 : 0x150]
    try:
        title_domestic = title_domestic.decode().strip()
    except:
        pass

    # overseas title
    title_overseas = data[0x150 : 0x180]
    try:
        title_overseas = title_overseas.decode().strip()
    except:
        pass

    # software type
    software_type = data[0x180 : 0x182]
    try:
        software_type = software_type.decode().strip()
    except:
        pass
    if software_type in GENESIS_SOFTWARE_TYPES:
        software_type = GENESIS_SOFTWARE_TYPES[software_type]

    # serial
    serial = data[0x182 : 0x18B]
    try:
        serial = serial.decode().strip()
    except:
        pass

    # revision
    revision = data[0x18C : 0x18E]
    try:
        revision = revision.decode().strip()
    except:
        pass

    # checksum
    checksum = unpack('>H', data[0x18E : 0x190])[0]

    # device support
    device_support = data[0x190 : 0x1A0]
    try:
        tmp = list()
        for v in device_support:
            if v < ord('!') or v > ord('~'):
                continue
            c = chr(v)
            if c in GENESIS_DEVICE_SUPPORT:
                tmp.append(GENESIS_DEVICE_SUPPORT[c])
            else:
                tmp.append(c)
        device_support = ' / '.join(s for s in sorted(tmp))
    except:
        pass
    if len(device_support) == 0:
        device_support = None

    # ROM/RAM start/end
    rom_start = unpack('>I', data[0x1A0 : 0x1A4])[0]
    rom_end = unpack('>I', data[0x1A4 : 0x1A8])[0]
    ram_start = unpack('>I', data[0x1A8 : 0x1AC])[0]
    ram_end = unpack('>I', data[0x1AC : 0x1B0])[0]

    # extra memory
    extra_memory = data[0x1B0 : 0x1BC]

    # modem support
    modem_support = data[0x1BC : 0x1C8]
    try:
        modem_support = modem_support.decode().strip()
    except:
        pass
    if len(modem_support) == 0:
        modem_support = None

    # region support
    region_support = data[0x1F0 : 0x1F3]
    try:
        tmp = list()
        for v in region_support:
            if v < ord('!') or v > ord('~'):
                continue
            c = chr(v)
            if c in GENESIS_REGION_SUPPORT:
                tmp.append(GENESIS_REGION_SUPPORT[c])
            else:
                tmp.append(c)
        region_support = ' / '.join(s for s in sorted(tmp))
    except:
        pass
    if len(region_support) == 0:
        region_support = None

    # identify game
    out = {
        'system_type': system_type,
        'publisher': publisher,
        'release_year': release_year,
        'release_month': release_month,
        'title_domestic': title_domestic,
        'title_overseas': title_overseas,
        'software_type': software_type,
        'serial': serial,
        'revision': revision,
        'checksum': '0x%s' % hex(checksum)[2:].zfill(4),
        'device_support': device_support,
        'rom_start': '0x%s' % hex(rom_start)[2:].zfill(8),
        'rom_end': '0x%s' % hex(rom_end)[2:].zfill(8),
        'ram_start': '0x%s' % hex(ram_start)[2:].zfill(8),
        'ram_end': '0x%s' % hex(ram_end)[2:].zfill(8),
        'extra_memory': '0x%s' % ''.join(hex(v)[2:].zfill(2) for v in extra_memory),
        'modem_support': modem_support,
        'region_support': region_support,
    }
    out['title'] = out['title_overseas']
    if isinstance(serial, str):
        gamedb_ID = ''.join(c if c in SAFE else '_' for c in serial).replace('-','')
        if gamedb_ID in db['Genesis']:
            gamedb_entry = db['Genesis'][gamedb_ID]
            for k,v in gamedb_entry.items():
                if (k not in out) or prefer_gamedb:
                    out[k] = v
    return out

# dictionary storing all identify functions
IDENTIFY = {
    'GB/GBC':  identify_gb_gbc,
    'GBA':     identify_gba,
    'GC':      identify_gc,
    'Genesis': identify_genesis,
    'N64':     identify_n64,
    'PSP':     identify_psp,
    'PSX':     identify_psx,
    'PS2':     identify_ps2,
    'SNES':    identify_snes,
}

# throw an error for unsupported consoles
def check_console(console):
    if console not in IDENTIFY:
        error("Invalid console: %s\nOptions: %s" % (console, ', '.join(sorted(IDENTIFY.keys()))))

# main program logic
def main():
    args = parse_args()
    db = load_db(args.database)
    meta = IDENTIFY[args.console](args.input, db, prefer_gamedb=args.prefer_gamedb)
    if meta is None:
        error("%s game not found: %s" % (args.console, args.input))
    f_out = open_file(args.output, 'wt')
    print('\n'.join('%s%s%s' % (k,args.delimiter,v) for k,v in meta.items()), file=f_out)
    f_out.close()

# run program
if __name__ == "__main__":
    if len(sys.argv) == 1:
        get_args_interactive(sys.argv)
    main()

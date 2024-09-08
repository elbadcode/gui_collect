import re
import struct

from pathlib import Path

# Major thanks to DarkStarSword
# https://github.com/DarkStarSword/3d-fixes/blob/cef49cbe6b324dc7a2041c1928f9b41678b3c61e/blender_3dmigoto.py#L113

u8_pattern  = re.compile(r'''(?:[RGBAD]8)+_UINT''')
u16_pattern = re.compile(r'''(?:[RGBAD]16)+_UINT''')
u32_pattern = re.compile(r'''(?:[RGBAD]32)+_UINT''')

s8_pattern  = re.compile(r'''(?:[RGBAD]8)+_SINT''')
s16_pattern = re.compile(r'''(?:[RGBAD]16)+_SINT''')
s32_pattern = re.compile(r'''(?:[RGBAD]32)+_SINT''')

f16_pattern = re.compile(r'''(?:[RGBAD]16)+_FLOAT''')
f32_pattern = re.compile(r'''(?:[RGBAD]32)+_FLOAT''')

unorm8_pattern  = re.compile(r'''(?:[RGBAD]8)+_UNORM''')
unorm16_pattern = re.compile(r'''(?:[RGBAD]16)+_UNORM''')

snorm8_pattern  = re.compile(r'''(?:[RGBAD]8)+_SNORM''')
snorm16_pattern = re.compile(r'''(?:[RGBAD]16)+_SNORM''')


def get_byte_width(dxgi_format: str):
    matches = re.findall(r'([0-9]+)', dxgi_format.split("_", maxsplit=1)[0])
    return sum([int(x) for x in matches]) // 8


def get_decoder(dxgi_format: str):
    matches = re.findall(r'([0-9]+)', dxgi_format.split("_", maxsplit=1)[0])
    component_count = len(matches)

    FORMAT = lambda x: '<{}'.format(x * component_count)

    # Build the struct once, instead of building it each time the lambda is called

    if f16_pattern.match(dxgi_format):
        unpack_from = struct.Struct(FORMAT('e')).unpack_from
        return lambda buffer, offset: unpack_from(buffer, offset)
    if f32_pattern.match(dxgi_format):
        unpack_from = struct.Struct(FORMAT('f')).unpack_from
        return lambda buffer, offset: unpack_from(buffer, offset)
    
    if u8_pattern.match(dxgi_format):
        unpack_from = struct.Struct(FORMAT('B')).unpack_from
        return lambda buffer, offset: unpack_from(buffer, offset)
    if u16_pattern.match(dxgi_format):
        unpack_from = struct.Struct(FORMAT('H')).unpack_from
        return lambda buffer, offset: unpack_from(buffer, offset)
    if u32_pattern.match(dxgi_format):
        unpack_from = struct.Struct(FORMAT('L')).unpack_from
        return lambda buffer, offset: unpack_from(buffer, offset)
    
    if s8_pattern.match(dxgi_format):
        unpack_from = struct.Struct(FORMAT('b')).unpack_from
        return lambda buffer, offset: unpack_from(buffer, offset)
    if s16_pattern.match(dxgi_format):
        unpack_from = struct.Struct(FORMAT('h')).unpack_from
        return lambda buffer, offset: unpack_from(buffer, offset)
    if s32_pattern.match(dxgi_format):
        unpack_from = struct.Struct(FORMAT('l')).unpack_from
        return lambda buffer, offset: unpack_from(buffer, offset)

    if unorm8_pattern.match(dxgi_format):
        unpack_from = struct.Struct(FORMAT('B')).unpack_from
        return lambda buffer, offset: [x/255.0 for x in unpack_from(buffer, offset)]
    if unorm16_pattern.match(dxgi_format):
        unpack_from = struct.Struct(FORMAT('H')).unpack_from
        return lambda buffer, offset: [x/65535.0 for x in unpack_from(buffer, offset)]

    if snorm8_pattern.match(dxgi_format):
        unpack_from = struct.Struct(FORMAT('b')).unpack_from
        return lambda buffer, offset: [x/127.0 for x in unpack_from(buffer, offset)]
    if snorm16_pattern.match(dxgi_format):
        unpack_from = struct.Struct(FORMAT('h')).unpack_from
        return lambda buffer, offset: [x/32767.0 for x in unpack_from(buffer, offset)]

    raise Exception('Unrecognized dxgi format: {}'.format(dxgi_format))


def collect_binary_buffer_data(buffer_path: Path, buffer_formats: list[str], buffer_stride: int):
    buffer = buffer_path.read_bytes()

    byte_offset    = 0
    decoder_offset = []
    for format in buffer_formats:
        decoder_offset.append((get_decoder(format), byte_offset))
        byte_offset += get_byte_width(format)

    vertex_count = len(buffer) // buffer_stride

    buffer_data = [
        [
            decoder(buffer, vertex_index * buffer_stride + offset)
            for decoder, offset in decoder_offset
        ]
        for vertex_index in range(vertex_count)
    ]

    return buffer_data
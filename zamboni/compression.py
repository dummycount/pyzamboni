from io import BytesIO
import ooz


def decompress_kraken(data: bytes, out_size: int) -> bytes:
    return ooz.decompress(data, out_size)


# TODO: rewrite as native code for performance?
def decompress_prs(data: bytes, out_size: int) -> bytes:
    in_stream = BytesIO(data)
    output = bytearray(out_size)

    out_index = 0
    ctrl_byte = 0
    ctrl_byte_counter = 1

    def read_byte():
        return in_stream.read(1)[0]

    def get_ctrl_bit():
        nonlocal ctrl_byte, ctrl_byte_counter

        ctrl_byte_counter -= 1
        if ctrl_byte_counter == 0:
            ctrl_byte = read_byte()
            ctrl_byte_counter = 8

        flag = bool(ctrl_byte & 0x1)
        ctrl_byte >>= 1
        return flag

    while out_index < out_size:
        if out_index > 182:
            pass

        while get_ctrl_bit():
            output[out_index] = read_byte()
            out_index += 1

        offset = 0
        load_size = 0

        if get_ctrl_bit():
            data0, data1 = in_stream.read(2)

            if data0 == 0 and data1 == 0:
                break

            offset = (data1 << 5) + (data0 >> 3) - 0x2000
            size = data0 & 0x7
            load_size = size + 2 if size != 0 else read_byte() + 10
        else:
            load_size = 2
            if get_ctrl_bit():
                load_size += 2
            if get_ctrl_bit():
                load_size += 1

            offset = read_byte() - 0x100

        load_index = out_index + offset

        for _ in range(load_size):
            output[out_index] = output[load_index]
            out_index += 1
            load_index += 1

    return bytes(output)

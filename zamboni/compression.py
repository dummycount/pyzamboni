from io import BytesIO
import ooz


def decompress_kraken(data: bytes, out_size: int) -> bytes:
    # TODO: rewrite to avoid external dependency
    return ooz.decompress(data, out_size)


def decompress_prs(data: bytes, out_size: int) -> bytes:
    in_stream = BytesIO(data)
    output = bytearray()

    ctrl_byte = 0
    ctrl_byte_counter = 1

    def read_byte():
        nonlocal in_stream
        if result := in_stream.read(1):
            return result[0]
        raise StopIteration()

    def get_ctrl_bit():
        nonlocal in_stream, ctrl_byte, ctrl_byte_counter

        ctrl_byte_counter -= 1
        if ctrl_byte_counter == 0:
            ctrl_byte = in_stream.read(1)[0]
            ctrl_byte_counter = 8

        flag = bool(ctrl_byte & 0x1)
        ctrl_byte >>= 1
        return flag

    try:
        while len(output) < out_size:
            while get_ctrl_bit():
                output.append(read_byte())

            control_offset = 0
            control_size = 0

            if get_ctrl_bit():
                if len(output) >= out_size:
                    break

                data0 = read_byte()
                data1 = read_byte()

                if data0 == 0 and data1 == 0:
                    break

                control_offset = (data1 << 5) + (data0 >> 3) - 0x2000
                size = data0 & 0x7
                control_size = size + 2 if size else read_byte() + 10
            else:
                control_size = 2
                if get_ctrl_bit():
                    control_size += 2
                if get_ctrl_bit():
                    control_size += 1

                control_offset = read_byte() - 0x100

            control_size = min(control_size, out_size - len(output))
            load_index = len(output) + control_offset
            output.extend(output[load_index : load_index + control_size])

    except StopIteration:
        pass

    return bytes(output)

import struct
from typing import Tuple

MASK = 0xFFFFFFFFFFFFFFFF


def reverse17(val):
    return val ^ (val >> 17) ^ (val >> 34) ^ (val >> 51)


def reverse23(val):
    return (val ^ (val << 23) ^ (val << 46)) & MASK


def xs128p(state):
    s1 = state[0] & MASK
    s0 = state[1] & MASK
    s1 ^= (s1 << 23) & MASK
    s1 ^= (s1 >> 17) & MASK
    s1 ^= s0 & MASK
    s1 ^= (s0 >> 26) & MASK
    state0 = state[1] & MASK
    state1 = s1 & MASK
    return state0, state1


def xs128p_backward(state):
    prev_state1 = state[0]
    prev_state0 = state[1] ^ (state[0] >> 26)
    prev_state0 = prev_state0 ^ state[0]
    prev_state0 = reverse17(prev_state0)
    prev_state0 = reverse23(prev_state0)
    return prev_state0, prev_state1

def mh3(h):
    h ^= h >> 33
    h = (h * 0xFF51AFD7ED558CCD) & MASK
    h ^= h >> 33
    h = (h * 0xC4CEB9FE1A85EC53) & MASK
    h ^= h >> 33
    return h


def mh3_inv(h):
    h ^= h >> 33
    h = (h * 0x9CB4B2F8129337DB) & MASK
    h ^= h >> 33
    h = (h * 0x4F74430C22A54005) & MASK
    h ^= h >> 33
    return h


def to_double(out):
    double_bits = ((out & MASK) >> 12) | 0x3FF0000000000000
    return struct.unpack("d", struct.pack("<Q", double_bits))[0] - 1


def state_str(s0, s1, offset):
    return f"({s0}, {s1})+{offset:>02}"

def seed_str(seed, offset):
    seed_hex = seed.to_bytes(8, "big").hex()
    return f"{seed_hex}{offset:+}"


def dbg_str(s0, s1, offset, note=None):
    state = state_str(s0, s1, offset)
    val = to_double(s0)
    return f"s={state:<47}  val={val:<22} {note or ''}"

class Rng(object):
    state: Tuple[int, int]
    offset: int

    @staticmethod
    def from_seed(seed: str | int, offset: int) -> 'Rng':
        if isinstance(seed, str):
            seed = int(seed, 16)

        state = (mh3(seed), mh3(seed^MASK))
        for _ in range(64):
            state = xs128p(state)
        rng = Rng(state, 63)
        rng.step(offset)
        return rng

    @staticmethod
    def parse(inp: str) -> 'Rng':
        import re
        m = re.match("\(([0-9]+),\s*([0-9]+)\)\+([0-9]+)", inp)
        if m:
            s0 = int(m.group(1))
            s1 = int(m.group(2))
            offset = int(m.group(3))
            return Rng((s0, s1), offset)
        
        m = re.match("([0-9a-fA-F]{,16})([\+\-][0-9]+)", inp)
        if m:
            seed = int(m.group(1), 16)
            offset = int(m.group(2))
            return Rng.from_seed(seed, offset)
            
    def find_seed(self, max_distance: int = 50_000_000):
        state = self.state
        for distance in range(max_distance):
            seed0 = mh3_inv(state[0])
            seed1 = mh3_inv(state[1]) ^ MASK
            if seed0 == seed1:
                if distance % 64 == 0:
                    distance -= 64
                steps_back = distance - (distance % 64) + ((-distance) % 64)
                # expected_offset = (distance-1) % 64
                # ^ use this to "correct" an rng instance
                return seed0, steps_back

            state = xs128p_backward(state)
        return None


    def __init__(self, state: Tuple[int, int], offset: int):
        self.state = state
        self.offset = offset

    def get_state(self) -> Tuple[int, int, int]:
        return self.state[0], self.state[1], self.offset

    def get_state_str(self) -> str:
        return state_str(self.state[0], self.state[1], self.offset)

    def value(self) -> float:
        return to_double(self.state[0])

    def next(self) -> float:
        return self.step(1)

    def prev(self) -> float:
        return self.step(-1)

    def step_raw(self, amount=1):
        if amount > 0:
            for _ in range(amount):
                self.state = xs128p(self.state)
        else:
            for _ in range(-amount):
                self.state = xs128p_backward(self.state)

    def step(self, steps=1):
        self.offset -= steps

        while self.offset < 0:
            self.step_raw(128)
            self.offset += 64

        while self.offset >= 64:
            self.step_raw(-128)
            self.offset -= 64

        self.step_raw(-steps)
        return self.value()

import functools
import itertools
import struct

from typing import TypedDict, Union

# original code by ubuntor: https://discord.com/channels/738107179294523402/875833188537208842/965050266258903070

MASK = 0xFFFFFFFFFFFFFFFF
MAX_KERNEL_BASIS_SIZE = 20

BitMatrix = list[int]


@functools.cache
def state_matrices(i: int) -> (BitMatrix, BitMatrix):
    """
    Develop the bit matrices which define state spaces
    """
    if i == 0:
        # Start with initial state
        return initial_state_matrices()
    # Otherwise, run Xorshift128+ on the prior set of [cached] states
    return xs128p_matrix(*state_matrices(i - 1))


def initial_state_matrices() -> tuple[BitMatrix, BitMatrix]:
    """
    As bits, initial state matrices look like weird offset identity matrices.
    The results are 128 bits wide and 64 rows tall, but at a smaller scale
    they look like this:

                         state0              state1

                        10000000            00001000
                        01000000            00000100
                        00100000            00000010
                        00010000            00000001
    """
    state0 = [0] * 64
    state1 = [0] * 64
    for i in range(64):
        state0[i] = 1 << (127 - i)
        state1[i] = 1 << (127 - (64 + i))
    return state0, state1


def xs128p_matrix(state0_matrix: BitMatrix, state1_matrix: BitMatrix) -> tuple[BitMatrix, BitMatrix]:
    """
    Equivalent to Xorshift128+ implementation across matrices of states.
    """
    state0_matrix = state0_matrix[:]
    state1_matrix = state1_matrix[:]
    s1, s0 = state0_matrix, state1_matrix
    s1 = xor_matrix(s1, lshift_matrix(s1, 23))
    s1 = xor_matrix(s1, rshift_matrix(s1, 17))
    s1 = xor_matrix(s1, s0)
    s1 = xor_matrix(s1, rshift_matrix(s0, 26))
    state0_matrix = state1_matrix
    state1_matrix = s1
    return state0_matrix, state1_matrix


def lshift_matrix(matrix: BitMatrix, n: int) -> BitMatrix:
    """
    "left-shift" the bit matrix by sliding it up N rows
    """
    return matrix[n:] + [0] * n


def rshift_matrix(matrix: BitMatrix, n: int) -> BitMatrix:
    """
    "right-shift" the bit matrix by sliding it down N rows
    """
    return [0] * n + matrix[:-n]


def xor_matrix(matrix1: BitMatrix, matrix2: BitMatrix) -> BitMatrix:
    """
    XOR two bit matrices together, row-wise
    """
    result = []
    for i in range(min(len(matrix1), len(matrix2))):
        result.append(matrix1[i] ^ matrix2[i])
    return result


def rref(matrix: BitMatrix, n: int) -> BitMatrix:
    """
    Reduced Row Echelon Form (RREF) of a matrix
    """
    matrix = matrix[:]
    num_rows = len(matrix)
    next_row = 0
    for col in range(n):
        col_bitmask = 1 << (n - 1 - col)
        for row in range(next_row, num_rows):
            if matrix[row] & col_bitmask:
                matrix[row], matrix[next_row] = matrix[next_row], matrix[row]
                for i in range(num_rows):
                    if i != next_row and (matrix[i] & col_bitmask):
                        matrix[i] ^= matrix[next_row]
                next_row += 1
                if next_row == num_rows:
                    return matrix
                break
    return matrix


def transpose(matrix: BitMatrix) -> BitMatrix:
    """
    Transposes a bit matrix. Assumes the input matrix is 128 bits wide.
    """
    num_rows = len(matrix)
    flipped = []
    for i in range(128):
        cell = 0
        for j in range(num_rows):
            cell += ((matrix[j] >> (127 - i)) & 1) << (num_rows - 1 - j)
        flipped.append(cell)
    return flipped


def powerset(s: list[int]) -> list[tuple[int, ...]]:
    """
    Given [1, 2], returns [(), (1,), (2,), (1, 2)]
    """
    return itertools.chain.from_iterable(itertools.combinations(s, r) for r in range(len(s) + 1))


def xs128p(state0: int, state1: int) -> tuple[int, int]:
    """
    Xorshift128+ implementation
    """
    s1 = state0 & MASK
    s0 = state1 & MASK
    s1 ^= (s1 << 23) & MASK
    s1 ^= (s1 >> 17) & MASK
    s1 ^= s0 & MASK
    s1 ^= (s0 >> 26) & MASK
    state0 = state1 & MASK
    state1 = s1 & MASK
    return state0, state1


def xs128p_backward(state0: int, state1: int) -> tuple[int, int]:
    """
    Inverse of Xorshift128+ implementation, steps state backwards by 1
    """
    prev_state1 = state0
    prev_state0 = state1 ^ (state0 >> 26)
    prev_state0 = prev_state0 ^ state0
    prev_state0 = reverse17(prev_state0)
    prev_state0 = reverse23(prev_state0)
    return prev_state0, prev_state1


def reverse17(val: int) -> int:
    return val ^ (val >> 17) ^ (val >> 34) ^ (val >> 51)


def reverse23(val: int) -> int:
    return (val ^ (val << 23) ^ (val << 46)) & MASK


def state_to_double(s0: int) -> float:
    double_bits = (s0 >> 12) | 0x3FF0000000000000
    return struct.unpack("d", struct.pack("<Q", double_bits))[0] - 1


def get_mantissa(val: float) -> int:
    if val == 1.0:
        return MASK >> 12
    return struct.unpack("<Q", struct.pack("d", val + 1))[0] & 0x000FFFFFFFFFFFFF


def int_to_bits(n: int, length: int) -> list[int]:
    return [(n >> (length - i - 1)) & 1 for i in range(length)]


def bits_to_int(bits: list[int]) -> int:
    return int("".join(map(str, bits)), 2)


def print_matrix(M: BitMatrix, n: int = 128) -> None:
    for row in M:
        print(f"{row:0{n}b}")
    print()


def solve_in_rng_order(
    knowns: list[Union[float, tuple[float, float], None]],
) -> list[tuple[int, int]]:
    """
    Determine valid RNG states which could output float values matching knowns

    knowns: list of constraints for consecutive RNG float outputs
    Each known can be:
        float               [known value between 0.0 and 1.0]
        (float, float)      [known range of (low, high) values]
        or None             [no constraint for this output]

    Returns list of all possible solutions (s0, s1), or [] if no solution found
    """
    bits: list[int] = []
    bits_matrix: BitMatrix = []

    for i, known in enumerate(knowns):
        state0_matrix, _ = state_matrices(i)
        if type(known) == float:
            mantissa = get_mantissa(known)
            known_bits = 52
            bits += int_to_bits(mantissa, known_bits)
            bits_matrix += state0_matrix[:known_bits]
        elif type(known) in [tuple, list]:
            lo, hi = known
            lo_mantissa = get_mantissa(lo)
            hi_mantissa = get_mantissa(hi)
            known_bits = 52 - (lo_mantissa ^ hi_mantissa).bit_length()
            bits += int_to_bits(lo_mantissa >> (52 - known_bits), known_bits)
            bits_matrix += state0_matrix[:known_bits]
        elif known is None:
            continue
        else:
            print("unknown type for known", known)
            1 / 0

    num_known_bits = len(bits)
    # print(f"solving with {num_known_bits}...")

    # find kernel basis (homogeneous solutions)
    kernel_basis = []

    M = transpose(bits_matrix)

    M = [(M[i] << 128) + (1 << (127 - i)) for i in range(128)]
    M = rref(M, num_known_bits + 128)
    for row in M:
        if row >> 128 == 0:
            kernel_basis.append(row & ((1 << 128) - 1))

    kernel_basis_size = len(kernel_basis)
    if kernel_basis_size > 0:
        print(f"WARNING: {2**kernel_basis_size} (2^{kernel_basis_size}) potential solutions")
        if kernel_basis_size > MAX_KERNEL_BASIS_SIZE:
            print("too many to bruteforce, giving up :(")
            return []

    # find particular solution
    M = [(bits_matrix[i] << 1) + bits[i] for i in range(len(bits_matrix))]
    M = rref(M, 129)

    particular_solution = 0
    for row in M:
        if row == 0:
            break
        if row == 1:
            # print('ERROR: contradiction found, no solution!')
            return []
        particular_solution += (row & 1) << (row.bit_length() - 2)

    solutions = []

    for homogeneous_solutions in powerset(kernel_basis):
        solution = particular_solution
        for vec in homogeneous_solutions:
            solution ^= vec
        s0 = solution >> 64
        s1 = solution & ((1 << 64) - 1)
        candidate_solution = (s0, s1)
        # test solution
        for known in knowns:
            value = state_to_double(s0)
            if type(known) == float:
                if known != value:
                    break
            elif type(known) in [tuple, list]:
                lo, hi = known
                if not (lo < value < hi):
                    break
            s0, s1 = xs128p(s0, s1)
        else:
            # good solution!
            # print('found solution', candidate_solution)
            solutions.append(candidate_solution)
    return solutions


BLOCK_SIZE = 64


class RNGStateSolution(TypedDict):
    state: tuple[int, int]
    offset: int
    roll: float
    crossesBlockBoundary: bool


def solve_in_math_random_order(
    rolls: list[Union[float, tuple[float, float], None]],
) -> list[RNGStateSolution]:
    """
    Math.random() generates blocks of 64 values, and then reverses them:

       block 1, roll 63
       block 1, roll 62
       block 1, roll 61
       ...
       block 1, roll  2
       block 1, roll  1
       block 1, roll  0
       block 2, roll 63   <- this value is generated 127 rolls *after*
       block 2, roll 62      the prior one which Math.random() outputted
       block 2, roll 61

    rolls: list of constraints for consecutive Math.random() float outputs
    Each roll can be:
        float               [known value between 0.0 and 1.0]
        (float, float)      [known range of (low, high) values]
        or None             [no constraint for this output]

    Returns list of all possible RNG solutions or [] if no solution found
    """
    solutions = []
    for offset in range(min(len(rolls), BLOCK_SIZE)):
        knowns = []
        if offset:
            block = rolls[0:offset][::-1]
            # If we have some initial offset, then the first block
            # needs to have the rest of the block filled out with nulls
            block.extend(None for _ in range(BLOCK_SIZE - len(block)))
            knowns.extend(block)

        for i in range(offset, len(rolls), BLOCK_SIZE):
            block = rolls[i : i + BLOCK_SIZE]
            # For every subsequent block, we need to fill the
            # start of the block with nulls instead of the end
            block.extend(None for _ in range(BLOCK_SIZE - len(block)))
            block = block[::-1]
            knowns.extend(block)

        states = solve_in_rng_order(knowns)
        if not states:
            continue

        for state in states:
            for i in range((offset or 64) - 1):
                state = xs128p(*state)

            solutions.append(
                {
                    "state": state,
                    "offset": (offset or 64) - 1,
                    "roll": state_to_double(state[0]),
                    "crossesBlockBoundary": len(knowns) > BLOCK_SIZE,
                }
            )

    return solutions
